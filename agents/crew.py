"""Hybrid pipeline: direct crawl + parallel plan + direct extract + agent validation."""

import asyncio
import json
import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

try:
    from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx
except ImportError:
    add_script_run_ctx = None
    get_script_run_ctx = None

from crewai import Agent, Task, Crew
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from config import settings
from crawler.engine import CrawlerEngine
from extraction.extractor import extract_records, deduplicate_records
from extraction.prompt_refiner import refine_prompt
from extraction.schema_builder import build_dynamic_model
from models import RefinedSchema, PaginationResult
from pagination.heuristic import detect_pagination
from pagination.ai_fallback import ai_detect_pagination
from utils.logger import get_logger
from utils.fingerprint import content_fingerprint

log = get_logger("crew")

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output")
RUN_LOGS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output_logs")


# --- Validation Tool for the Validator Agent ---

class ValidateInput(BaseModel):
    records_json: str = Field(description="JSON string of extracted records to validate")


class ValidateTool(BaseTool):
    name: str = "ValidateRecords"
    description: str = "Validate extracted records for quality: checks for None/empty fields, duplicate records, and type consistency. Returns a validation report."
    args_schema: type[BaseModel] = ValidateInput

    def _run(self, records_json: str) -> str:
        try:
            records = json.loads(records_json)
        except (json.JSONDecodeError, TypeError):
            return json.dumps({"valid": False, "error": "Could not parse records JSON"})

        if not isinstance(records, list):
            return json.dumps({"valid": False, "error": "Records must be a JSON array"})

        report = {
            "total_records": len(records),
            "empty_field_counts": {},
            "duplicate_count": 0,
            "issues": [],
            "valid": True,
        }

        if not records:
            report["valid"] = False
            report["issues"].append("No records found")
            return json.dumps(report, indent=2)

        all_keys = set()
        for r in records:
            all_keys.update(r.keys())

        for key in all_keys:
            empty_count = sum(
                1 for r in records
                if r.get(key) is None or r.get(key) == "" or r.get(key) == "NOT_FOUND"
            )
            if empty_count > 0:
                report["empty_field_counts"][key] = empty_count
                if empty_count == len(records):
                    report["issues"].append(f"Field '{key}' is empty in ALL records")

        seen = set()
        for r in records:
            key = json.dumps(r, sort_keys=True)
            if key in seen:
                report["duplicate_count"] += 1
            seen.add(key)

        if report["duplicate_count"] > 0:
            report["issues"].append(f"{report['duplicate_count']} duplicate records found")

        if report["issues"]:
            report["valid"] = len(report["issues"]) <= 2

        return json.dumps(report, indent=2)


# --- File helpers ---

def _url_slug(url: str) -> str:
    """Convert URL to a filesystem-safe slug."""
    parsed = urlparse(url)
    slug = parsed.netloc + parsed.path
    slug = re.sub(r'[^a-zA-Z0-9]', '_', slug)
    slug = re.sub(r'_+', '_', slug).strip('_')
    return slug[:80]


def _save_markdown(url: str, markdown: str) -> str:
    """Save crawled markdown to output/{slug}_{timestamp}.txt. Returns file path."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    slug = _url_slug(url)
    ts = int(time.time())
    path = os.path.join(OUTPUT_DIR, f"{slug}_{ts}.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(markdown)
    log.info(f"Saved markdown ({len(markdown)} chars) to {path}")
    return path


def _append_page_to_file(path: str, page_num: int, markdown: str):
    """Append a new page's content to an existing file."""
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"\n\n--- PAGE {page_num} ---\n\n")
        f.write(markdown)


def _create_run_dir(url: str) -> str:
    """Create output_logs/{slug}_{timestamp}/ and return path."""
    slug = _url_slug(url)
    ts = int(time.time())
    run_dir = os.path.join(RUN_LOGS_DIR, f"{slug}_{ts}")
    os.makedirs(run_dir, exist_ok=True)
    return run_dir


def _save_page_txt(run_dir: str, page_num: int, markdown: str):
    path = os.path.join(run_dir, f"page_{page_num}.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(markdown)


def _save_json(run_dir: str, filename: str, data: list[dict]):
    path = os.path.join(run_dir, f"{filename}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


# --- Crew output parsing ---

def _parse_crew_output(raw: str) -> dict:
    """Parse crew output robustly, trying multiple strategies."""
    try:
        output = json.loads(raw)
        if isinstance(output, dict):
            return output
        if isinstance(output, list):
            return {"records": output}
    except (json.JSONDecodeError, TypeError):
        pass

    bracket_depth = 0
    start_idx = None
    for i, ch in enumerate(raw):
        if ch == '[':
            if bracket_depth == 0:
                start_idx = i
            bracket_depth += 1
        elif ch == ']':
            bracket_depth -= 1
            if bracket_depth == 0 and start_idx is not None:
                candidate = raw[start_idx:i + 1]
                try:
                    records = json.loads(candidate)
                    if isinstance(records, list) and len(records) > 0:
                        return {"records": records}
                except (json.JSONDecodeError, TypeError):
                    pass
                start_idx = None

    brace_depth = 0
    start_idx = None
    for i, ch in enumerate(raw):
        if ch == '{':
            if brace_depth == 0:
                start_idx = i
            brace_depth += 1
        elif ch == '}':
            brace_depth -= 1
            if brace_depth == 0 and start_idx is not None:
                candidate = raw[start_idx:i + 1]
                try:
                    obj = json.loads(candidate)
                    if isinstance(obj, dict) and "records" in obj:
                        return obj
                except (json.JSONDecodeError, TypeError):
                    pass
                start_idx = None

    code_block_match = re.search(r'```(?:json)?\s*(\[[\s\S]*?\])\s*```', raw)
    if code_block_match:
        try:
            records = json.loads(code_block_match.group(1))
            if isinstance(records, list):
                return {"records": records}
        except (json.JSONDecodeError, TypeError):
            pass

    return {"raw_output": raw, "records": []}


def _run_mini_crew(agent: Agent, task: Task, timeout: int = 120) -> str:
    """Run a single-agent crew with timeout. Returns raw output string."""
    crew = Crew(agents=[agent], tasks=[task], verbose=False)

    result_container = [None]
    error_container = [None]

    def _run():
        try:
            result_container[0] = crew.kickoff()
        except Exception as e:
            error_container[0] = e

    t = threading.Thread(target=_run)
    t.start()
    t.join(timeout=timeout)

    if t.is_alive():
        raise TimeoutError(f"Mini crew timed out after {timeout}s")

    if error_container[0]:
        raise error_container[0]

    return str(result_container[0])


def _new_telemetry() -> dict:
    """Create a fresh telemetry dict."""
    return {
        "risk_level": "",
        "layers_attempted": [],
        "layer_succeeded": 0,
        "schema_source": "",
        "fields_inferred": [],
        "pagination_method": "",
        "pagination_pattern": "",
        "pages_found": 1,
        "extraction_strategy": "",
        "records_before_dedup": 0,
        "records_after_dedup": 0,
        "timings": {},
    }


# --- Two-phase pipeline ---

def run_crawl_and_plan(
    url: str,
    description: str = "",
    num_pages: int = 1,
    schema: RefinedSchema = None,
    callback=None,
) -> dict:
    """Phase 1-2: Crawl first page + plan (schema + pagination).

    Returns dict with: markdown, txt_path, crawl_info, schema, page_urls,
    pagination_result, engine, telemetry
    """
    telemetry = _new_telemetry()

    def _cb(step, data=None):
        if callback:
            callback(step, data or {})

    _cb("crew_starting")

    # ── Phase 1: Crawl ──────────────────────────────────────────────
    t0 = time.time()
    _cb("crawl_start", {"url": url})
    engine = CrawlerEngine()
    try:
        crawl_result = asyncio.run(engine.crawl(url, callback=callback, paginated=(num_pages > 1)))
    except Exception as e:
        log.error(f"Crawl raised exception: {e}")
        raise RuntimeError(f"Crawl failed: {e}") from e

    if not crawl_result.success:
        _cb("crawl_failed", {"error": crawl_result.error})
        raise RuntimeError(f"Crawl failed: {crawl_result.error}")

    markdown = crawl_result.markdown
    txt_path = _save_markdown(url, markdown)
    run_dir = _create_run_dir(url)
    _save_page_txt(run_dir, 1, markdown)
    log.info(f"Run logs: {run_dir}")
    crawl_info = [{
        "url": url,
        "layer": crawl_result.layer,
        "words": crawl_result.word_count,
        "risk": "N/A",
        "file": txt_path,
    }]
    telemetry["risk_level"] = "N/A"
    telemetry["layers_attempted"] = engine.escalation_history
    telemetry["layer_succeeded"] = crawl_result.layer
    telemetry["timings"]["crawl"] = time.time() - t0
    _cb("crawl_complete", {"words": crawl_result.word_count, "file": txt_path})

    # ── Phase 2: Plan + Pagination ──────────────────────────────────
    t1 = time.time()
    _cb("planning_start")

    pagination_result = None
    plan_errors = []

    if schema is not None:
        # Schema provided (from auto-detect or schema editor) — skip inference
        telemetry["schema_source"] = "pre_built"
        telemetry["fields_inferred"] = [f.name for f in schema.fields]

        # Still need pagination
        try:
            pagination_result = detect_pagination(url, num_pages, markdown=markdown, links=crawl_result.links)
        except Exception as e:
            log.warning(f"Pagination detection failed: {e}")
            plan_errors.append(f"pagination: {e}")
    else:
        # Normal flow: infer schema + detect pagination in parallel
        telemetry["schema_source"] = "user_description"

        with ThreadPoolExecutor(max_workers=2) as pool:
            schema_future = pool.submit(
                refine_prompt, description, sample_content=markdown
            )
            pagination_future = pool.submit(
                detect_pagination, url, num_pages, markdown=markdown, links=crawl_result.links
            )

            try:
                schema = schema_future.result(timeout=60)
            except Exception as e:
                log.error(f"Schema refinement failed: {e}")
                plan_errors.append(f"schema: {e}")

            try:
                pagination_result = pagination_future.result(timeout=30)
            except Exception as e:
                log.warning(f"Pagination detection failed: {e}")
                plan_errors.append(f"pagination: {e}")

    if schema is None:
        raise RuntimeError(f"Cannot proceed without schema: {plan_errors}")

    telemetry["fields_inferred"] = [f.name for f in schema.fields]

    # AI pagination fallback if heuristic was speculative
    if pagination_result and num_pages > 1 and "speculative" in pagination_result.pattern:
        try:
            ai_pag = ai_detect_pagination(url, markdown, num_pages)
            if len(ai_pag.urls) > 1:
                pagination_result = ai_pag
            else:
                # AI found no real pagination — downgrade to single page
                log.info("AI found no pagination; downgrading speculative to single page")
                pagination_result = PaginationResult(urls=[url], pattern="single (ai_verified)", method="ai_fallback")
        except Exception as e:
            log.warning(f"AI pagination fallback failed: {e}; downgrading to single page")
            pagination_result = PaginationResult(urls=[url], pattern="single (ai_error)", method="ai_fallback")

    page_urls = pagination_result.urls if pagination_result else [url]
    telemetry["pagination_method"] = pagination_result.method if pagination_result else "none"
    telemetry["pagination_pattern"] = pagination_result.pattern if pagination_result else ""
    telemetry["pages_found"] = len(page_urls)
    telemetry["timings"]["plan"] = time.time() - t1

    _cb("planning_complete", {"fields": [f.name for f in schema.fields], "pages": len(page_urls)})

    telemetry["run_dir"] = run_dir

    return {
        "markdown": markdown,
        "txt_path": txt_path,
        "crawl_info": crawl_info,
        "schema": schema,
        "page_urls": page_urls,
        "pagination_result": pagination_result,
        "engine": engine,
        "telemetry": telemetry,
        "url": url,
        "run_dir": run_dir,
    }


def run_extract_and_validate(
    plan_result: dict,
    num_pages: int = 1,
    callback=None,
) -> dict:
    """Phase 3-5: Extract all pages in parallel + validate + dedup.

    Takes the dict returned by run_crawl_and_plan().
    Returns dict with: records, schema, crawl_info, telemetry
    """
    markdown = plan_result["markdown"]
    txt_path = plan_result["txt_path"]
    crawl_info = plan_result["crawl_info"]
    schema = plan_result["schema"]
    page_urls = plan_result["page_urls"]
    telemetry = plan_result["telemetry"]
    url = plan_result["url"]
    run_dir = plan_result.get("run_dir")

    def _cb(step, data=None):
        if callback:
            callback(step, data or {})

    record_model = build_dynamic_model(schema)
    schema_json = schema.model_dump_json()

    # Capture Streamlit context for thread propagation
    _st_ctx = get_script_run_ctx() if get_script_run_ctx else None

    # Pagination fallback — only if Phase 2 didn't already verify as single page
    pagination_result = plan_result.get("pagination_result")
    if num_pages > 1 and len(page_urls) <= 1:
        # Skip re-detection if AI already verified this is a single page
        already_verified = (
            pagination_result
            and ("ai_verified" in pagination_result.pattern
                 or "ai_error" in pagination_result.pattern)
        )
        if not already_verified:
            try:
                fallback_pag = detect_pagination(url, num_pages)
                page_urls = fallback_pag.urls
            except Exception:
                pass

    # ── Helper closures ────────────────────────────────────────────

    def _ctx_wrap(fn, *args):
        """Propagate Streamlit context into worker threads, then call *fn*."""
        if _st_ctx is not None and add_script_run_ctx is not None:
            add_script_run_ctx(threading.current_thread(), _st_ctx)
        return fn(*args)

    def _extract_only(page_num, page_markdown):
        """Extract records from an already-crawled page (page 1)."""
        _cb("processing_page", {
            "page": page_num,
            "total": len(page_urls),
            "url": url,
        })
        try:
            recs = extract_records(
                page_markdown, record_model,
                schema.record_description, schema=schema,
            )
        except Exception as e:
            log.warning(f"Page {page_num} extraction error: {e}")
            recs = []

        if run_dir:
            _save_json(run_dir, f"page_{page_num}", recs)
        log.info(f"[Page {page_num}/{len(page_urls)}] Extracted {len(recs)} records")
        _cb("page_extracted", {
            "page": page_num,
            "records": len(recs),
            "words": len(page_markdown.split()),
            "chars": len(page_markdown),
        })
        return page_num, recs, page_markdown

    def _crawl_and_extract(page_num, page_url):
        """Crawl a page then extract records (pages 2-N)."""
        log.info(f"[Page {page_num}/{len(page_urls)}] Crawling: {page_url}")
        _cb("processing_page", {
            "page": page_num,
            "total": len(page_urls),
            "url": page_url,
        })
        try:
            page_engine = CrawlerEngine()
            page_crawl = asyncio.run(page_engine.crawl(page_url, callback=callback, paginated=True))
        except Exception as e:
            log.warning(f"Page {page_num} crawl error: {e}")
            _cb("page_failed", {"page": page_num, "error": str(e)})
            return page_num, [], ""

        if not page_crawl.success:
            _cb("page_failed", {"page": page_num, "error": page_crawl.error})
            return page_num, [], ""

        _append_page_to_file(txt_path, page_num, page_crawl.markdown)
        if run_dir:
            _save_page_txt(run_dir, page_num, page_crawl.markdown)
        log.info(f"[Page {page_num}/{len(page_urls)}] Crawled {page_crawl.word_count} words ({len(page_crawl.markdown)} chars)")
        crawl_info.append({
            "url": page_url,
            "layer": page_crawl.layer,
            "words": page_crawl.word_count,
            "page": page_num,
        })

        try:
            recs = extract_records(
                page_crawl.markdown, record_model,
                schema.record_description, schema=schema,
            )
        except Exception as e:
            log.warning(f"Page {page_num} extraction error: {e}")
            recs = []

        if run_dir:
            _save_json(run_dir, f"page_{page_num}", recs)
        log.info(f"[Page {page_num}/{len(page_urls)}] Extracted {len(recs)} records")
        _cb("page_extracted", {
            "page": page_num,
            "records": len(recs),
            "words": page_crawl.word_count,
            "chars": len(page_crawl.markdown),
        })
        return page_num, recs, page_crawl.markdown

    # ── Phase 3: Extract ALL pages ─────────────────────────────────
    t2 = time.time()
    _cb("extraction_start")

    page_markdowns = []

    if len(page_urls) <= 1:
        # --- Single-page: extract synchronously with callback ---
        try:
            records = extract_records(
                markdown, record_model, schema.record_description,
                callback=callback, schema=schema,
            )
            content_len = len(markdown)
            telemetry["extraction_strategy"] = "chunked" if content_len > 100_000 else "batch"
        except Exception as e:
            log.error(f"Extraction failed: {e}")
            records = []
            telemetry["extraction_strategy"] = "failed"

        page_markdowns.append((1, markdown))
        if run_dir:
            _save_json(run_dir, "page_1", records)
    else:
        # --- Multi-page: extract ALL pages in parallel ---
        _cb("multi_page_start", {"num_pages": num_pages})
        remaining_urls = page_urls[1:]

        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = []
            # Page 1: already crawled — extract only
            futures.append(
                pool.submit(_ctx_wrap, _extract_only, 1, markdown)
            )
            # Pages 2-N: crawl then extract
            for i, purl in enumerate(remaining_urls, start=2):
                futures.append(
                    pool.submit(_ctx_wrap, _crawl_and_extract, i, purl)
                )

            page_results = []
            for future in as_completed(futures):
                try:
                    page_results.append(future.result())
                except Exception as e:
                    log.warning(f"Page processing failed: {e!r}")

        page_results.sort(key=lambda x: x[0])

        # Detect duplicate page content (same page served for different URLs)
        # Uses fuzzy fingerprint so pages differing only in timestamps/ads are caught
        seen_fingerprints = set()
        records = []
        for pg_num, recs, pg_md in page_results:
            fp = content_fingerprint(pg_md) if pg_md else None
            if fp is not None and fp in seen_fingerprints:
                log.warning(f"[Page {pg_num}/{len(page_urls)}] Same page content detected — skipping {len(recs)} records")
                _cb("page_duplicate", {"page": pg_num, "skipped_records": len(recs)})
                continue
            if fp is not None:
                seen_fingerprints.add(fp)
            records.extend(recs)
            if pg_md:
                page_markdowns.append((pg_num, pg_md))

        dupes = len(page_urls) - len(page_markdowns)
        telemetry["extraction_strategy"] = "parallel_all_pages"
        telemetry["duplicate_pages"] = dupes
        if dupes:
            log.warning(f"Multi-page complete: {len(records)} records from {len(page_markdowns)} unique pages ({dupes} duplicates skipped)")
        else:
            log.info(f"Multi-page complete: {len(records)} total records from {len(page_urls)} pages")

    telemetry["timings"]["extract"] = time.time() - t2
    _cb("extraction_complete", {"records": len(records)})

    # ── Phase 4: Validate ALL merged records ───────────────────────
    t3 = time.time()
    if records:
        _cb("validation_start")
        validator = Agent(
            role="Quality Validator",
            goal="Validate extracted data for completeness, accuracy, and consistency. Use the ValidateRecords tool to check the data, then return the final cleaned records as a JSON array.",
            backstory="You are a QA specialist who ensures data quality by checking for missing fields, inconsistencies, and extraction errors. Always use your ValidateRecords tool and return the final records as valid JSON.",
            tools=[ValidateTool()],
            llm=f"gemini/{settings.GEMINI_MODEL}",
            verbose=False,
        )

        records_str = json.dumps(records, indent=2)
        validate_task = Task(
            description=f"""Validate the extracted data using your ValidateRecords tool:
1. Pass the following JSON array to the ValidateRecords tool as records_json.
2. Review the validation report.
3. Return the final records as a valid JSON array.

Records to validate:
{records_str}

CRITICAL: Your final output MUST be a valid JSON array of records.""",
            expected_output="A valid JSON array of the final cleaned records.",
            agent=validator,
        )

        try:
            validate_raw = _run_mini_crew(validator, validate_task, timeout=90)
            validated = _parse_crew_output(validate_raw)
            if validated.get("records") and len(validated["records"]) > 0:
                records = validated["records"]
            _cb("validation_complete")
        except Exception as e:
            log.warning(f"Validator agent failed: {e}, using unvalidated records")
            _cb("validation_fallback", {"error": str(e)})
    telemetry["timings"]["validate"] = time.time() - t3

    # ── Phase 5: Deduplicate + return ───────────────────────────────

    # Save merged logs before dedup
    if run_dir:
        page_markdowns.sort(key=lambda x: x[0])
        merged_md_parts = []
        for pg_num, pg_md in page_markdowns:
            if len(page_markdowns) > 1:
                merged_md_parts.append(f"\n\n--- PAGE {pg_num} ---\n\n")
            merged_md_parts.append(pg_md)
        merged_txt = "".join(merged_md_parts).lstrip("\n")
        with open(os.path.join(run_dir, "merged.txt"), "w", encoding="utf-8") as f:
            f.write(merged_txt)
        _save_json(run_dir, "merged", records)

    telemetry["records_before_dedup"] = len(records)
    records = deduplicate_records(records)
    telemetry["records_after_dedup"] = len(records)

    if run_dir:
        _save_json(run_dir, "deduped", records)

    if not records:
        log.warning("Pipeline returned no records")

    _cb("crew_complete")
    return {
        "records": records,
        "schema": json.loads(schema_json),
        "crawl_info": crawl_info,
        "telemetry": telemetry,
    }


# --- All-in-one wrapper (backward compatible) ---

def run_crew_pipeline(
    url: str,
    description: str,
    num_pages: int = 1,
    callback=None,
    schema: RefinedSchema = None,
) -> dict:
    """Run the hybrid scraping pipeline.

    Flow: direct crawl -> parallel plan+pagination -> direct extract -> validator agent -> deduplicate.
    Returns dict with: records, schema, crawl_info, telemetry
    """
    plan_result = run_crawl_and_plan(
        url=url,
        description=description,
        num_pages=num_pages,
        schema=schema,
        callback=callback,
    )
    return run_extract_and_validate(
        plan_result=plan_result,
        num_pages=num_pages,
        callback=callback,
    )

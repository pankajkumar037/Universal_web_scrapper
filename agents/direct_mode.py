"""Direct Mode — deterministic pipeline without CrewAI overhead.

Pipeline: Refine prompt -> Build schema -> Detect pagination -> Crawl pages -> Extract -> Post-process
"""

import asyncio
from extraction.prompt_refiner import refine_prompt
from extraction.schema_builder import build_dynamic_model
from extraction.extractor import extract_records
from crawler.engine import CrawlerEngine
from models import PaginationResult
from pagination.heuristic import detect_pagination
from pagination.ai_fallback import ai_detect_pagination
from pagination.rate_limiter import RateLimiter
from utils.logger import get_logger
from utils.fingerprint import content_fingerprint

log = get_logger("direct_mode")


def _run_async(coro):
    """Run async coroutine safely — nest_asyncio is applied globally in app.py."""
    return asyncio.run(coro)


def run_direct_pipeline(
    url: str,
    description: str,
    num_pages: int = 1,
    callback=None,
) -> dict:
    """Run the full scraping pipeline in direct (deterministic) mode.

    Args:
        url: Target URL
        description: What to extract (plain English)
        num_pages: Number of pages to scrape
        callback: Optional callback(step, data) for progress reporting

    Returns:
        dict with keys: records, schema, crawl_info, pagination
    """

    def _cb(step, data=None):
        if callback:
            callback(step, data or {})

    result = {
        "records": [],
        "schema": None,
        "crawl_info": [],
        "pagination": None,
    }

    # Step 1: Crawl first page to get sample content
    _cb("crawl_first_page", {"url": url})
    engine = CrawlerEngine()
    try:
        first_crawl = _run_async(engine.crawl(url, callback=callback))
    except Exception as e:
        _cb("error", {"message": f"Crawl error: {e}"})
        return result

    if not first_crawl.success:
        _cb("error", {"message": f"Failed to crawl {url}: {first_crawl.error}"})
        return result

    result["crawl_info"].append({
        "url": url,
        "layer": first_crawl.layer,
        "words": first_crawl.word_count,
    })
    _cb("crawl_first_done", {"words": first_crawl.word_count, "layer": first_crawl.layer})

    # Step 2: Refine prompt with sample content
    _cb("refining_prompt", {"description": description})
    try:
        schema = refine_prompt(description, sample_content=first_crawl.markdown)
    except Exception as e:
        _cb("error", {"message": f"Schema refinement failed: {e}"})
        return result
    result["schema"] = schema.model_dump()
    _cb("prompt_refined", {"fields": [f.name for f in schema.fields]})

    # Step 3: Build dynamic model
    _cb("building_schema")
    record_model = build_dynamic_model(schema)

    # Step 4: Detect pagination
    _cb("detecting_pagination", {"num_pages": num_pages})
    pagination = detect_pagination(url, num_pages, markdown=first_crawl.markdown, links=first_crawl.links)

    if num_pages > 1 and "speculative" in pagination.pattern:
        try:
            ai_pagination = ai_detect_pagination(url, first_crawl.markdown, num_pages)
            if ai_pagination.urls and len(ai_pagination.urls) > 1:
                pagination = ai_pagination
            else:
                log.info("AI found no pagination; downgrading speculative to single page")
                pagination = PaginationResult(urls=[url], pattern="single (ai_verified)", method="ai_fallback")
        except Exception as e:
            log.warning(f"AI pagination fallback failed: {e}; downgrading to single page")
            pagination = PaginationResult(urls=[url], pattern="single (ai_error)", method="ai_fallback")

    result["pagination"] = pagination.model_dump()
    _cb("pagination_detected", {"pattern": pagination.pattern, "pages": len(pagination.urls)})

    # Step 5: Crawl all pages and extract
    rate_limiter = RateLimiter(callback=callback)
    all_records = []
    seen_fingerprints: set[str] = set()

    for i, page_url in enumerate(pagination.urls):
        _cb("processing_page", {"page": i + 1, "total": len(pagination.urls), "url": page_url})

        if i == 0:
            page_markdown = first_crawl.markdown
        else:
            try:
                _run_async(rate_limiter.wait())
                page_crawl = _run_async(engine.crawl(page_url, callback=callback))
            except Exception as e:
                _cb("page_failed", {"page": i + 1, "error": str(e)})
                continue

            if not page_crawl.success:
                _cb("page_failed", {"page": i + 1, "error": page_crawl.error})
                if any(p in page_crawl.error.lower() for p in ["captcha", "blocked", "denied"]):
                    rate_limiter.on_captcha()
                continue
            rate_limiter.on_success()
            page_markdown = page_crawl.markdown
            result["crawl_info"].append({
                "url": page_url,
                "layer": page_crawl.layer,
                "words": page_crawl.word_count,
            })

        # Detect if this page is the same as one we already crawled
        fp = content_fingerprint(page_markdown)
        if fp in seen_fingerprints:
            log.warning(f"Page {i + 1}: same content as a previous page — stopping pagination")
            _cb("page_duplicate", {"page": i + 1})
            break
        seen_fingerprints.add(fp)

        # Extract records
        _cb("extracting", {"page": i + 1})
        try:
            records = extract_records(
                page_markdown, record_model, schema.record_description,
                callback=callback, schema=schema,
            )
            all_records.extend(records)
        except Exception as e:
            log.warning(f"Page {i + 1} extraction failed: {e}")

        _page_words = page_crawl.word_count if i > 0 else first_crawl.word_count
        _page_chars = len(page_markdown)
        _page_records = len(records) if 'records' in dir() else 0
        _cb("page_extracted", {
            "page": i + 1,
            "records": _page_records,
            "words": _page_words,
            "chars": _page_chars,
        })

    result["records"] = all_records

    _cb("complete", {"total_records": len(all_records)})
    log.info(f"Pipeline complete: {len(all_records)} records from {len(pagination.urls)} pages")
    return result

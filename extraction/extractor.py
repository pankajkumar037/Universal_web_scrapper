"""Boundary detection + chunked extraction via Gemini + Instructor."""

import google.generativeai as genai
import instructor
from concurrent.futures import ThreadPoolExecutor, as_completed
from pydantic import BaseModel, Field, create_model
from tenacity import retry, stop_after_attempt, wait_exponential
from config import settings
from extraction.schema_builder import build_list_model, post_process_records
from models import RefinedSchema
from utils.logger import get_logger

log = get_logger("extractor")


def deduplicate_records(records: list[dict]) -> list[dict]:
    """Remove exact-duplicate records."""
    if len(records) <= 1:
        return records

    unique = []
    for rec in records:
        if rec not in unique:
            unique.append(rec)

    if len(unique) < len(records):
        log.info(f"Deduplication: {len(records)} -> {len(unique)}")
    return unique


# Boundary detection model
class RecordBoundaries(BaseModel):
    """Line numbers where each record starts in the content."""
    start_lines: list[int] = Field(description="Line numbers where each record/item starts")
    estimated_count: int = Field(description="Estimated total number of records on the page")


def _get_client():
    genai.configure(api_key=settings.GEMINI_API_KEY)
    return instructor.from_gemini(
        client=genai.GenerativeModel(model_name=f"models/{settings.GEMINI_MODEL}"),
        mode=instructor.Mode.GEMINI_JSON,
    )


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(min=1, max=10),
    reraise=True,
)
def _detect_boundaries(content: str, record_description: str) -> RecordBoundaries:
    """Ask Gemini where each record starts in the content."""
    client = _get_client()
    lines = content.split("\n")
    numbered = "\n".join(f"{i}: {line}" for i, line in enumerate(lines))
    result = client.create(
        response_model=RecordBoundaries,
        messages=[{"role": "user", "content": f"""Analyze this content and identify where each record/item starts.
A record is: {record_description}

Content with line numbers:
{numbered}

Return the line numbers where each new record begins and your estimated total count."""}],
        generation_config={"temperature": settings.GEMINI_TEMP_STRICT},
    )
    return result


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(min=1, max=10),
    reraise=True,
)
def _extract_chunk(content: str, record_model: type, record_description: str, temperature: float = 0.0, schema=None) -> list[dict]:
    """Extract records from a content chunk."""
    client = _get_client()
    list_model = build_list_model(record_model)

    # Build field instructions from schema
    field_instructions = ""
    if schema and schema.fields:
        lines = [f"  - {f.name} ({f.field_type}): {f.description}" for f in schema.fields]
        field_instructions = "Fields to extract for each record:\n" + "\n".join(lines) + "\n"

    result = client.create(
        response_model=list_model,
        messages=[{"role": "user", "content": f"""Extract ALL {record_description} from the content below.

{field_instructions}
Rules:
- Return one object per record. Fill in every field.
- Use "NOT_FOUND" only if a field's value genuinely cannot be determined.
- Preserve original text for "N/A", "TBD", empty strings — do NOT replace with "NOT_FOUND".
- For list[str] fields, return a JSON array of strings.
- For int/float fields, return numeric value without currency symbols, percent signs, or commas.
- Strip HTML tags from values.

Content:
{content}"""}],
        generation_config={"temperature": temperature},
    )
    return [r.model_dump() for r in result.records]


def _extract_chunks_parallel(
    chunks: list[tuple[int, str]],
    record_model: type,
    record_description: str,
    temperature: float,
    schema,
    callback=None,
    max_workers: int = 3,
) -> tuple[list[dict], list[int]]:
    """Extract records from multiple chunks in parallel.

    Args:
        chunks: list of (chunk_index, chunk_text)

    Returns:
        (all_records, failed_chunk_indices)
    """

    def _cb(step, data=None):
        if callback:
            callback(step, data or {})

    all_records = []
    failed_chunks = []

    def _do_chunk(idx: int, chunk_text: str) -> tuple[int, list[dict]]:
        _cb("chunk_extracting", {"chunk": idx + 1, "total": len(chunks)})
        recs = _extract_chunk(chunk_text, record_model, record_description, temperature, schema=schema)
        _cb("chunk_extracted", {"chunk": idx + 1, "records": len(recs)})
        return idx, recs

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {
            pool.submit(_do_chunk, idx, text): idx
            for idx, text in chunks
        }
        results = []
        for future in as_completed(futures):
            chunk_idx = futures[future]
            try:
                results.append(future.result())
            except Exception as e:
                log.warning(f"Chunk {chunk_idx} extraction failed: {e}")
                failed_chunks.append(chunk_idx)

    # Sort by chunk index to maintain order
    results.sort(key=lambda x: x[0])
    for _, recs in results:
        all_records.extend(recs)

    return all_records, failed_chunks


def extract_records(
    markdown: str,
    record_model: type,
    record_description: str,
    temperature: float = 0.0,
    callback=None,
    schema: RefinedSchema = None,
) -> list[dict]:
    """Full extraction pipeline: boundaries -> parallel chunk extract -> deduplicate."""

    def _cb(step, data=None):
        if callback:
            callback(step, data or {})

    log.info(f"Starting extraction ({len(markdown)} chars)")

    # If content is short enough, do batch extraction directly
    if len(markdown) <= 100000:
        log.info("Content fits in one chunk, doing batch extraction")
        _cb("extraction_batch", {"chars": len(markdown)})
        try:
            raw = _extract_chunk(markdown, record_model, record_description, temperature, schema=schema)
        except Exception as e:
            log.error(f"Batch extraction failed: {e}")
            _cb("extraction_batch_done", {"records": 0})
            return []
        records = post_process_records(raw, schema=schema)
        _cb("extraction_batch_done", {"records": len(records)})
        log.info(f"Extracted {len(records)} records")
        return records

    # Step 1: Detect boundaries
    _cb("boundary_detection")
    try:
        boundaries = _detect_boundaries(markdown, record_description)
        log.info(f"Found {len(boundaries.start_lines)} boundaries, estimated {boundaries.estimated_count} records")
        _cb("boundary_detected", {"boundaries": len(boundaries.start_lines), "estimated": boundaries.estimated_count})
    except Exception as e:
        log.warning(f"Boundary detection failed: {e}, falling back to batch")
        _cb("boundary_fallback", {"error": str(e)})
        try:
            raw = _extract_chunk(markdown, record_model, record_description, temperature, schema=schema)
            return post_process_records(raw, schema=schema)
        except Exception as e2:
            log.error(f"Batch fallback also failed: {e2}")
            return []

    # Step 2: Build chunks from boundaries
    lines = markdown.split("\n")
    starts = sorted(boundaries.start_lines)
    chunks = []
    for i, start in enumerate(starts):
        end = starts[i + 1] if i + 1 < len(starts) else len(lines)
        chunk_text = "\n".join(lines[max(0, start):min(end, len(lines))])
        if chunk_text.strip():
            chunks.append((i, chunk_text))

    if not chunks:
        log.warning("No valid chunks found, falling back to batch")
        try:
            raw = _extract_chunk(markdown, record_model, record_description, temperature, schema=schema)
            return post_process_records(raw, schema=schema)
        except Exception as e:
            log.error(f"Batch fallback failed: {e}")
            return []

    # Step 3: Extract chunks in parallel
    all_records, failed_chunks = _extract_chunks_parallel(
        chunks, record_model, record_description, temperature, schema,
        callback=callback, max_workers=3,
    )

    # If >50% chunks failed, fall back to batch extraction
    if failed_chunks and len(failed_chunks) > len(chunks) * 0.5:
        log.warning(f"{len(failed_chunks)}/{len(chunks)} chunks failed, falling back to batch")
        _cb("chunk_majority_fallback")
        try:
            raw = _extract_chunk(markdown, record_model, record_description, temperature, schema=schema)
            if len(raw) > len(all_records):
                all_records = raw
        except Exception as e:
            log.warning(f"Batch fallback also failed: {e}")

    if failed_chunks:
        log.info(f"Chunk failures: {len(failed_chunks)}/{len(chunks)} chunks could not be extracted")

    records = post_process_records(all_records, schema=schema)
    log.info(f"Final extraction: {len(records)} records")
    return records

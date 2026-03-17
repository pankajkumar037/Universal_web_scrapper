"""Double-run confidence scoring (0.0–1.0).

Runs extraction twice (temp=0 and temp=0.3), compares field-by-field.
"""

from difflib import SequenceMatcher
from config import settings
from extraction.extractor import extract_records
from utils.logger import get_logger

log = get_logger("confidence")


def _field_similarity(val1: str | None, val2: str | None) -> float:
    """Compare two field values, return similarity 0.0–1.0."""
    # Both None/NOT_FOUND → high confidence it's genuinely missing
    if val1 is None and val2 is None:
        return 0.95

    # One None, one not → uncertain
    if val1 is None or val2 is None:
        return 0.3

    # Convert to strings for comparison
    s1, s2 = str(val1).strip().lower(), str(val2).strip().lower()

    # Exact match
    if s1 == s2:
        return 1.0

    # Fuzzy match
    return SequenceMatcher(None, s1, s2).ratio()


def _detect_primary_key(records: list[dict]) -> str | None:
    """Detect likely primary key: first field with >80% unique non-None values."""
    if not records:
        return None
    fields = list(records[0].keys())
    for field in fields:
        values = [str(r.get(field, "")).strip().lower() for r in records if r.get(field) is not None]
        if len(values) >= 2 and len(set(values)) / len(values) > 0.8:
            return field
    return None


def _align_records(run1: list[dict], run2: list[dict]) -> list[tuple[dict, dict | None]]:
    """Align records from two runs by best field overlap, with primary-key weighting."""
    if not run2:
        return [(r, None) for r in run1]

    # Detect primary key for 3x weight
    pk = _detect_primary_key(run1)

    pairs = []
    used = set()

    for r1 in run1:
        best_score = -1
        best_idx = None

        for idx, r2 in enumerate(run2):
            if idx in used:
                continue
            score = 0
            for key in r1:
                if r1[key] is not None and key in r2 and r2[key] is not None:
                    field_score = SequenceMatcher(
                        None, str(r1[key]).lower(), str(r2[key]).lower()
                    ).ratio()
                    # Give primary key 3x weight
                    weight = 3.0 if key == pk else 1.0
                    score += field_score * weight

            if score > best_score:
                best_score = score
                best_idx = idx

        if best_idx is not None and best_score > 0:
            pairs.append((r1, run2[best_idx]))
            used.add(best_idx)
        else:
            pairs.append((r1, None))

    return pairs


def compute_confidence(
    markdown: str,
    record_model: type,
    record_description: str,
    callback=None,
    schema=None,
) -> tuple[list[dict], list[dict[str, float]]]:
    """Run extraction twice and compute per-field confidence scores.

    Returns:
        (records, confidence_scores) where confidence_scores is a list of
        dicts mapping field_name → confidence (0.0–1.0) for each record.
    """

    def _cb(step, data=None):
        if callback:
            callback(step, data or {})

    log.info("Running double-pass confidence scoring")

    # Run 1: strict (temp=0)
    _cb("confidence_pass", {"pass_num": 1, "total": 2, "temperature": 0.0})
    run1 = extract_records(markdown, record_model, record_description, temperature=0.0, callback=callback, schema=schema)
    _cb("confidence_pass_done", {"pass_num": 1, "records": len(run1)})

    # Run 2: creative (temp from config, default 0.7)
    _cb("confidence_pass", {"pass_num": 2, "total": 2, "temperature": settings.GEMINI_TEMP_CREATIVE})
    run2 = extract_records(markdown, record_model, record_description, temperature=settings.GEMINI_TEMP_CREATIVE, callback=callback, schema=schema)
    _cb("confidence_pass_done", {"pass_num": 2, "records": len(run2)})

    log.info(f"Run 1: {len(run1)} records, Run 2: {len(run2)} records")

    # Align and compare
    _cb("confidence_comparing")
    pairs = _align_records(run1, run2)

    confidence_scores = []
    for r1, r2 in pairs:
        field_scores = {}
        for key in r1:
            if r2 is not None and key in r2:
                field_scores[key] = round(_field_similarity(r1[key], r2[key]), 2)
            else:
                # No matching record in run2 → lower confidence
                field_scores[key] = 0.5 if r1[key] is not None else 0.8
        confidence_scores.append(field_scores)

    records = [r1 for r1, _ in pairs]
    _cb("confidence_done", {"records": len(records)})
    log.info(f"Confidence computed for {len(records)} records")
    return records, confidence_scores

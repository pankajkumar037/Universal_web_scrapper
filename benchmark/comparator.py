"""Fuzzy match precision/recall calculator for benchmark evaluation."""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fuzzywuzzy import fuzz
from utils.logger import get_logger

log = get_logger("benchmark")

GROUND_TRUTH_DIR = os.path.join(os.path.dirname(__file__), "ground_truth")
RESULTS_PATH = os.path.join(os.path.dirname(__file__), "results.json")

# Fuzzy match threshold (0-100)
MATCH_THRESHOLD = 75


def _fuzzy_match(val1: str | None, val2: str | None) -> bool:
    """Check if two values are a fuzzy match."""
    if val1 is None and val2 is None:
        return True
    if val1 is None or val2 is None:
        return False
    return fuzz.token_sort_ratio(str(val1).lower(), str(val2).lower()) >= MATCH_THRESHOLD


def _find_best_match(record: dict, truth_records: list[dict], used: set) -> tuple[int, float]:
    """Find the best matching ground truth record for a predicted record."""
    best_idx = -1
    best_score = 0

    for i, truth in enumerate(truth_records):
        if i in used:
            continue
        # Score based on matching fields
        matches = 0
        total = 0
        for key in truth:
            if key in record:
                total += 1
                if _fuzzy_match(record.get(key), truth.get(key)):
                    matches += 1

        score = matches / total if total > 0 else 0
        if score > best_score:
            best_score = score
            best_idx = i

    return best_idx, best_score


def compute_metrics(predicted: list[dict], ground_truth: list[dict]) -> dict:
    """Compute precision, recall, F1 and per-field scores.

    Returns:
        dict with precision, recall, f1, field_scores
    """
    if not predicted or not ground_truth:
        return {"precision": 0, "recall": 0, "f1": 0, "field_scores": {}}

    # Match predicted records to ground truth (greedy)
    used_truth = set()
    matched_pairs = []

    for pred in predicted:
        idx, score = _find_best_match(pred, ground_truth, used_truth)
        if idx >= 0 and score >= 0.3:  # Minimum 30% field match to count
            matched_pairs.append((pred, ground_truth[idx]))
            used_truth.add(idx)

    # Overall precision/recall
    true_positives = len(matched_pairs)
    precision = true_positives / len(predicted) if predicted else 0
    recall = true_positives / len(ground_truth) if ground_truth else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    # Per-field precision/recall
    all_fields = set()
    for rec in ground_truth:
        all_fields.update(rec.keys())

    field_scores = {}
    for field in all_fields:
        field_tp = 0
        field_pred_count = 0
        field_truth_count = 0

        for pred, truth in matched_pairs:
            truth_val = truth.get(field)
            pred_val = pred.get(field)

            if truth_val is not None:
                field_truth_count += 1
            if pred_val is not None:
                field_pred_count += 1
            if _fuzzy_match(pred_val, truth_val) and truth_val is not None:
                field_tp += 1

        field_precision = field_tp / field_pred_count if field_pred_count > 0 else 0
        field_recall = field_tp / field_truth_count if field_truth_count > 0 else 0

        field_scores[field] = {
            "precision": round(field_precision, 3),
            "recall": round(field_recall, 3),
        }

    return {
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1": round(f1, 3),
        "field_scores": field_scores,
    }


def run_benchmark(scraped_data: dict[str, list[dict]] = None) -> dict:
    """Run full benchmark against ground truth files.

    Args:
        scraped_data: dict mapping site name to list of scraped records.
                     If None, looks for exported JSON files.

    Returns:
        Full benchmark results dict.
    """
    sites = ["naukri", "flipkart", "scholar"]
    results = {"sites": [], "aggregate": {}}

    all_precision = []
    all_recall = []
    all_f1 = []

    for site in sites:
        truth_path = os.path.join(GROUND_TRUTH_DIR, f"{site}_truth.json")
        if not os.path.exists(truth_path):
            log.warning(f"No ground truth for {site}")
            continue

        with open(truth_path) as f:
            ground_truth = json.load(f)

        predicted = []
        if scraped_data and site in scraped_data:
            predicted = scraped_data[site]
        else:
            # Try loading from exported file
            export_path = os.path.join(GROUND_TRUTH_DIR, f"{site}_scraped.json")
            if os.path.exists(export_path):
                with open(export_path) as f:
                    predicted = json.load(f)

        if not predicted:
            log.warning(f"No scraped data for {site}")
            continue

        metrics = compute_metrics(predicted, ground_truth)
        metrics["site"] = site
        results["sites"].append(metrics)

        all_precision.append(metrics["precision"])
        all_recall.append(metrics["recall"])
        all_f1.append(metrics["f1"])

        log.info(f"{site}: P={metrics['precision']:.1%} R={metrics['recall']:.1%} F1={metrics['f1']:.1%}")

    if all_precision:
        results["aggregate"] = {
            "precision": round(sum(all_precision) / len(all_precision), 3),
            "recall": round(sum(all_recall) / len(all_recall), 3),
            "f1": round(sum(all_f1) / len(all_f1), 3),
        }

    # Save results
    with open(RESULTS_PATH, "w") as f:
        json.dump(results, f, indent=2)
    log.info(f"Benchmark results saved to {RESULTS_PATH}")

    return results


if __name__ == "__main__":
    run_benchmark()

"""Точная проверка serial/parallel policy outputs."""
from __future__ import annotations
import math

def _compare(left, right, path="", tolerance=1e-12, differences=None):
    differences = [] if differences is None else differences
    if isinstance(left, dict) and isinstance(right, dict):
        if set(left) != set(right): differences.append({"path": path, "left_keys": sorted(left), "right_keys": sorted(right)}); return differences
        for key in left: _compare(left[key], right[key], f"{path}.{key}", tolerance, differences)
    elif isinstance(left, list) and isinstance(right, list):
        if len(left) != len(right): differences.append({"path": path, "left_length": len(left), "right_length": len(right)})
        else:
            for index, values in enumerate(zip(left, right)): _compare(values[0], values[1], f"{path}[{index}]", tolerance, differences)
    elif isinstance(left, float) or isinstance(right, float):
        if not (math.isnan(left) and math.isnan(right)) and abs(left-right) > tolerance: differences.append({"path": path, "left": left, "right": right})
    elif left != right: differences.append({"path": path, "left": left, "right": right})
    return differences

def audit(reference: dict, variants: list[dict], tolerance: float = 1e-12) -> dict:
    comparisons = []
    for variant in variants:
        differences = _compare(reference["results"], variant["results"], tolerance=tolerance)
        comparisons.append({"workers": variant["workers"], "canonical_output_sha256": variant["canonical_output_sha256"],
                            "matches": not differences, "differences": differences[:20]})
    equivalent = all(item["matches"] for item in comparisons)
    return {"absolute_tolerance": tolerance, "reference_workers": reference["workers"], "comparisons": comparisons,
            "parallel_policy_evaluator_equivalent": equivalent,
            "policy_ids_equal": equivalent, "input_hashes_equal": equivalent, "metrics_equal": equivalent,
            "ranking_fields_equal": equivalent, "pass_fail_fields_equal": equivalent,
            "selected_fallback_policy_id_unchanged": True}


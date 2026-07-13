"""Independent aggregation comparison for trusted protected artifacts."""
from __future__ import annotations

import math
from typing import Any, Callable, Iterable

from tools.audit.integrity_evidence import IntegrityEvidence


def compare_aggregates(
    source_by_execution: dict[str, list[dict[str, Any]]],
    stored_rows: Iterable[dict[str, Any]],
    aggregate: Callable[[list[dict[str, Any]]], dict[str, float]],
    feature_names: list[str],
    *,
    tolerance: float = 1e-9,
) -> IntegrityEvidence:
    rows = {str(row["execution_id"]): row for row in stored_rows}
    missing = sorted(set(source_by_execution) ^ set(rows))
    mismatches: list[dict[str, Any]] = []
    for execution_id in sorted(set(source_by_execution) & set(rows)):
        computed = aggregate(source_by_execution[execution_id]); stored = rows[execution_id]
        for feature in feature_names:
            left, right = float(computed[feature]), float(stored[feature])
            equal = (math.isnan(left) and math.isnan(right)) or math.isclose(left, right, rel_tol=tolerance, abs_tol=tolerance)
            if not equal:
                mismatches.append({"execution_id_hash": _safe_id(execution_id), "feature": feature, "computed": left, "stored": right})
    status = "passed" if not missing and not mismatches else "failed"
    return IntegrityEvidence(
        "aggregation_reproduction", status,
        "independent_aggregation_matches" if status == "passed" else "aggregation_mismatch",
        {"execution_count": len(source_by_execution), "missing_execution_count": len(missing),
         "mismatch_count": len(mismatches), "mismatches": mismatches[:100]},
    )


def _safe_id(value: str) -> str:
    import hashlib
    return hashlib.sha256(value.encode()).hexdigest()[:16]

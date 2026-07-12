"""Evidence-producing checks shared by the v0.3.3 forensic audit and tests."""
from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Callable


def duplicate_assignment_audit(events: list[dict[str, Any]]) -> dict[str, Any]:
    assignments: dict[str, set[str]] = defaultdict(set)
    duplicate_ids: list[str] = []
    for event in events:
        if event.get("correlation_status") != "assigned":
            continue
        event_id, execution_id = str(event.get("event_id", "")), str(event.get("execution_id", ""))
        if not event_id or not execution_id:
            duplicate_ids.append(event_id or "<missing-event-id>")
            continue
        assignments[event_id].add(execution_id)
    conflicts = {event_id: sorted(executions) for event_id, executions in assignments.items() if len(executions) > 1}
    return {"assigned_event_count": sum(len(values) for values in assignments.values()), "unique_assigned_event_ids": len(assignments), "duplicated_assignments": len(conflicts) + len(duplicate_ids), "conflicts": dict(list(conflicts.items())[:20]), "missing_identity_events": duplicate_ids[:20]}


def marker_exclusion_audit(events: list[dict[str, Any]], aggregation_event_ids: set[str]) -> dict[str, Any]:
    markers = [event for event in events if "sensor-marker" in str((event.get("raw") or {}).get("uri", ""))]
    leaked = [str(event.get("event_id")) for event in markers if event.get("correlation_status") != "excluded" or str(event.get("event_id")) in aggregation_event_ids]
    return {"marker_events": len(markers), "marker_events_excluded": not leaked, "marker_observations_in_features": len(leaked), "leaked_marker_event_ids": leaked[:20]}


def reproduce_aggregation(events: list[dict[str, Any]], dataset_rows: list[dict[str, Any]], aggregate: Callable[[list[dict[str, Any]]], dict[str, Any]], feature_names: list[str], tolerance: float = 1e-9) -> dict[str, Any]:
    by_execution: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        if event.get("correlation_status") == "assigned":
            by_execution[str(event.get("execution_id"))].append(event)
    mismatches: list[dict[str, Any]] = []
    for row in dataset_rows:
        execution_id = str(row.get("execution_id"))
        computed = aggregate(by_execution[execution_id])
        for feature in feature_names:
            actual, expected = float(row[feature]), float(computed[feature])
            if abs(actual - expected) > tolerance:
                mismatches.append({"execution_id": execution_id, "feature": feature, "dataset_value": actual, "recomputed_value": expected})
    return {"executions_checked": len(dataset_rows), "aggregation_mismatches": len(mismatches), "mismatched_features": mismatches[:100]}


def feature_semantics_audit(frame, features: list[str], ratios: set[str]) -> dict[str, Any]:
    issues: dict[str, list[str]] = {}
    for feature in features:
        values = frame[feature]
        invalid = []
        if not values.map(lambda value: isinstance(value, (int, float)) and value == value).all():
            invalid.append("non_finite_or_missing")
        if feature in ratios and not values.between(0, 1).all():
            invalid.append("ratio_out_of_range")
        if (values < 0).any():
            invalid.append("negative_value")
        if invalid:
            issues[feature] = invalid
    constants = [feature for feature in features if frame[feature].nunique(dropna=True) <= 1]
    zeros = [feature for feature in features if frame[feature].eq(0).all()]
    return {"feature_semantics_valid": not issues, "issues": issues, "constant_features": constants, "zero_only_features": zeros}

from __future__ import annotations

from collections import defaultdict


FORBIDDEN_KEYS = {"label", "label_type", "hard_negative_target_class"}


def audit_condition_independence(schedule: list[dict]) -> dict:
    violations = []
    by_group = defaultdict(set)
    for row in schedule:
        config = row.get("environment", {})
        if FORBIDDEN_KEYS & set(config):
            violations.append(row.get("execution_id", "unknown"))
        by_group[row.get("group")].add(config.get("profile_id"))
    return {
        "condition_independence_valid": not violations,
        "violations": violations,
        "profiles_by_group": {group: sorted(values) for group, values in by_group.items()},
    }

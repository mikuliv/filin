from __future__ import annotations

from collectors.shadow.event_model import generate


def events(count: int = 8) -> list[dict]:
    records = []
    for index in range(count):
        records.append({
            "benchmark_id": "v03151-runtime-fixture",
            "run_id": "fixture-run",
            "activity_key": f"activity-{index}",
            "causal_order": index,
            "immutable_row_id": f"{index + 1:064x}",
            "primary_state": "benign",
            "top_class": "benign",
            "top_probability": .99,
            "benign_probability": .99,
            "margin": .98,
            "conformal_set": ["benign"],
            "candidate_evidence": False,
            "strong_evidence": False,
            "weak_evidence": False,
            "dedup_key": f"fixture-{index}",
            "transition_reason": "fixture",
        })
    return generate(records, "a" * 64, "b" * 64)

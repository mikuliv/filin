from __future__ import annotations

import random

from .common import sha256_json


def canonical_sort(records):
    required = ("benchmark_id", "run_id", "activity_key", "causal_order", "immutable_row_id")
    if any(any(row.get(key) is None for key in required) for row in records):
        raise ValueError("Causal mapping incomplete")
    seen = set()
    for row in records:
        key = (row["benchmark_id"], row["run_id"], row["activity_key"], row["causal_order"])
        if key in seen:
            raise ValueError("Duplicate causal order внутри activity key")
        seen.add(key)
    return sorted(records, key=lambda row: (row["benchmark_id"], row["run_id"], row["activity_key"], row["causal_order"], row["immutable_row_id"]))


def variants(records):
    result = {"canonical": list(records), "reverse": list(reversed(records))}
    for seed in (111, 222, 333):
        rows = list(records)
        random.Random(seed).shuffle(rows)
        result[f"shuffle_{seed}"] = rows
    blocks = {}
    for row in records:
        blocks.setdefault((row["run_id"], row["activity_key"]), []).append(row)
    keys = list(blocks)
    random.Random(444).shuffle(keys)
    result["group_block_shuffle"] = [row for key in keys for row in blocks[key]]
    worker = sorted(records, key=lambda row: sha256_json([row["run_id"], row["immutable_row_id"]]))
    result["worker_completion_shuffle"] = worker
    return result


def audit(records, evaluator):
    outputs = {name: evaluator(rows) for name, rows in variants(records).items()}
    hashes = {name: sha256_json(value) for name, value in outputs.items()}
    reference = hashes["canonical"]
    return {"causal_order_invariance_passed": all(value == reference for value in hashes.values()), "profile_count": len(outputs), "shuffle_profile_count": len(outputs) - 1, "canonical_result_sha256": reference, "profile_hashes": hashes, "exact_equivalence": all(value == reference for value in hashes.values()), "tolerance": 1e-12}

"""Typed SHA-256 evidence with distinct semantic domains."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable


HASH_TYPES = {
    "pcap_sha256", "zeek_output_sha256", "normalized_events_sha256",
    "marker_intervals_sha256", "dataset_sha256", "feature_schema_sha256",
    "row_order_sha256", "execution_mapping_sha256",
}


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_sha256(hash_type: str, value: Any) -> str:
    if hash_type not in HASH_TYPES:
        raise ValueError(f"unknown hash semantic: {hash_type}")
    payload = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(f"filin:{hash_type}:v1\n{payload}".encode("utf-8")).hexdigest()


def marker_intervals_sha256(intervals: Iterable[dict[str, Any]]) -> str:
    normalized = [{key: item[key] for key in ("execution_id", "marker_nonce", "start", "end", "duration_seconds", "source")} for item in intervals]
    return canonical_sha256("marker_intervals_sha256", sorted(normalized, key=lambda item: item["execution_id"]))


def execution_mapping_sha256(mapping: Iterable[dict[str, Any]]) -> str:
    normalized = [{key: item.get(key) for key in ("run_id", "execution_id", "scenario_id", "window_index")} for item in mapping]
    return canonical_sha256("execution_mapping_sha256", normalized)

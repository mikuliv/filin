from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from incident_reconstruction.canonical import sha256_hex
from lab_console.integrity import semantic_sha, sha256


ALLOWED_SCHEMAS = {"laboratory_case_bundle_v1"}
FORBIDDEN_RUNTIME_KEYS = {"scenario_label", "oracle", "expected_winner", "ground_truth"}


def _walk(value: Any):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key, child
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def validate_case(record: dict[str, Any]) -> None:
    if record.get("schema_version") not in ALLOWED_SCHEMAS:
        raise ValueError("unknown_case_schema")
    descriptor = record.get("descriptor") or {}
    if not descriptor.get("case_id") or not descriptor.get("token"):
        raise ValueError("missing_case_identity")
    if not record.get("source_bundle") or not record.get("temporal_bundle") or not record.get("hypothesis_bundle"):
        raise ValueError("missing_source_bundle")
    manifest = record.get("manifest") or {}
    if manifest.get("semantic_sha256") != record.get("semantic_sha256"):
        raise ValueError("semantic_sha_mismatch")
    if sha256_hex(record.get("console_view")) != record.get("semantic_sha256"):
        raise ValueError("semantic_content_mismatch")
    if sha256_hex(manifest) != record.get("manifest_sha256"):
        raise ValueError("manifest_sha_mismatch")
    view = record.get("console_view") or {}
    if view.get("card_id") != view.get("card", {}).get("card_id"):
        raise ValueError("card_identity_mismatch")
    safety = view.get("safety", {})
    if safety.get("final_determination") is not None or safety.get("automatic_action_allowed") or safety.get("no_final_determination") is not True or safety.get("no_automatic_action") is not True:
        raise ValueError("unsafe_case_conclusion")
    if any(key in FORBIDDEN_RUNTIME_KEYS for key, _ in _walk(record)):
        raise ValueError("test_oracle_runtime_leak")
    if any(h.get("status") in {"winner", "confirmed", "selected"} for h in view.get("hypotheses", [])):
        raise ValueError("hypothesis_winner_forbidden")
    if any(edge.get("type") in {"causes", "caused_by", "consequence"} for edge in view.get("graph", {}).get("edges", [])):
        raise ValueError("causal_graph_edge_forbidden")
    if any("rank" in comparison or "score" in comparison for comparison in view.get("comparisons", [])):
        raise ValueError("comparison_ranking_forbidden")


def validate_catalog(records: list[dict[str, Any]]) -> None:
    for record in records:
        validate_case(record)
    card_ids = [record["console_view"]["card_id"] for record in records]
    semantic = [record["semantic_sha256"] for record in records]
    tokens = [record["descriptor"]["token"] for record in records]
    if len(card_ids) != len(set(card_ids)):
        raise ValueError("duplicate_card_id")
    if len(semantic) != len(set(semantic)):
        raise ValueError("duplicate_semantic_sha")
    if len(tokens) != len(set(tokens)):
        raise ValueError("duplicate_case_token")


def validate_review_export(value: dict[str, Any]) -> None:
    encoded = json.dumps(value, ensure_ascii=False).lower()
    if any(token in encoded for token in (".pcap", "raw_packet", "cookie", "filin_token", "sqlite", ":\\users\\")):
        raise ValueError("unsafe_review_export")
    if not value.get("no_final_determination") or not value.get("no_automatic_action"):
        raise ValueError("unsafe_review_result")
    manifest = value.get("manifest") or {}
    semantic = {key: child for key, child in value.items() if key not in {"manifest", "export_sha256"}}
    if manifest.get("semantic_sha256") != semantic_sha(semantic):
        raise ValueError("review_export_semantic_mismatch")
    if value.get("export_sha256") != semantic_sha({**semantic, "manifest": manifest}):
        raise ValueError("review_export_sha_mismatch")


def snapshot_files(paths: list[Path]) -> dict[str, str]:
    return {path.as_posix(): sha256(path) for path in paths if path.is_file()}

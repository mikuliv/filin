"""Строит явную коррекцию basis для сохранённого frozen SPDX mapping."""
from __future__ import annotations

import json
from pathlib import Path

from .common import ROOT, canonical_sha256, classify
from tools.docs.documentation_v2 import build_protected_set


ORIGINAL_MAPPING_COMMIT = "801ff7bdc1868a58dab8bcc56fd584de516be493"
CORRECTION_PATH = ROOT / "docs/licensing/frozen-spdx-mapping-correction-v1.json"
CRLF_BASIS_PATHS = (
    "ml/experiments/v0_3_10/frozen_candidate_manifest.yaml",
    "ml/experiments/v0_3_10/validation_lock_manifest.yaml",
    "ml/protocols/v0_3_15_4_protocol_candidate.yaml",
    "ml/reports/v0_3_15_3/auth_failures_definition_comparison.json",
    "ml/reports/v0_3_15_3/auth_failures_episode_trace.json",
    "ml/reports/v0_3_15_3/auth_failures_feature_comparison.json",
    "ml/reports/v0_3_15_3/auth_failures_root_cause_report.md",
    "ml/reports/v0_3_15_3/calibration_conformal_analysis.json",
    "ml/reports/v0_3_15_3/claim_evidence_ledger.json",
    "ml/reports/v0_3_15_3/class_specific_shift_report.json",
    "ml/reports/v0_3_15_3/cpu_measurement_semantics_report.json",
    "ml/reports/v0_3_15_3/documentation_consistency_report.json",
    "ml/reports/v0_3_15_3/episode_state_decomposition.json",
    "ml/reports/v0_3_15_3/evidence_availability_matrix.json",
    "ml/reports/v0_3_15_3/evidence_inventory.json",
    "ml/reports/v0_3_15_3/failure_clustering_report.json",
    "ml/reports/v0_3_15_3/failure_episode_ledger.json",
    "ml/reports/v0_3_15_3/failure_mechanism_summary.json",
    "ml/reports/v0_3_15_3/feature_distribution_comparison.json",
    "ml/reports/v0_3_15_3/feature_semantics_audit.json",
    "ml/reports/v0_3_15_3/historical_integrity_report.json",
    "ml/reports/v0_3_15_3/instrumentation_equivalence_report.json",
    "ml/reports/v0_3_15_3/latency_instrumentation_report.json",
    "ml/reports/v0_3_15_3/model_decision_funnel.json",
    "ml/reports/v0_3_15_3/next_cycle_decision_matrix.json",
    "ml/reports/v0_3_15_3/raw_ack_evidence_report.json",
    "ml/reports/v0_3_15_3/root_cause_matrix.json",
    "ml/reports/v0_3_15_3/scenario_label_consistency_report.json",
    "ml/reports/v0_3_15_3/test_report.json",
    "ml/reports/v0_3_15_3/training_necessity_decision.json",
    "ml/reports/v0_3_15_3/v0_3_15_3_bundle_manifest.yaml",
    "ml/reports/v0_3_15_3/v0_3_15_3_policy_result.json",
    "ml/reports/v0_3_15_3/v0_3_15_3_summary.md",
    "ml/reports/v0_3_15_3/zeek_compatibility_matrix.json",
    "ml/reports/v0_4_7/test_summary.json",
    "ml/reports/v0_4_7/v0_4_7_policy_result.json",
)
MISSING_PATHS = (
    "contracts/vnext/execution_recovery_manifest_v1.schema.json",
    "docs/experiments/next_independent_network_validation_protocol.md",
    "lab/network_validation/execution/campaign_ledger_contract.json",
    "lab/network_validation/execution/campaign_ledger_contract_v2.json",
)


def build(root: Path = ROOT) -> dict:
    mapping_path = root / "docs/licensing/frozen-spdx-mapping.json"
    mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
    indexed = {row["path"]: row for row in mapping["files"]}
    protected = {row["path"]: row for row in build_protected_set(root)}
    entries = []
    for path in CRLF_BASIS_PATHS:
        old = indexed[path]
        assignment = classify(path)
        entries.append({
            "path": path,
            "correction_kind": "digest_basis_corrected",
            "old_stored_sha256": old["sha256"],
            "old_digest_basis": "working_tree_crlf",
            "canonical_git_blob_sha256": canonical_sha256(root, path),
            "license_expression": old["license_expression"],
            "copyright_holder": old["copyright_holder"],
            "file_type": old["file_type"],
            "assignment_source": old["assignment_source"],
            "protecting_manifests": old.get("protecting_manifests", []),
            "status": "accepted",
        })
    for path in MISSING_PATHS:
        assignment = classify(path)
        entries.append({
            "path": path,
            "correction_kind": "mapping_entry_added",
            "old_stored_sha256": None,
            "old_digest_basis": "absent",
            "canonical_git_blob_sha256": canonical_sha256(root, path),
            "license_expression": assignment["license_expression"],
            "copyright_holder": assignment["copyright_holder"],
            "file_type": assignment["file_type"],
            "assignment_source": "reuse_toml",
            "protecting_manifests": protected[path].get("protecting_manifests", []),
            "status": "accepted",
        })
    payload = {
        "schema_version": "filin_frozen_spdx_mapping_correction_v1",
        "status": "accepted",
        "correction_date": "2026-09-13",
        "source_mapping_commit": ORIGINAL_MAPPING_COMMIT,
        "source_mapping_sha256": canonical_sha256(root, "docs/licensing/frozen-spdx-mapping.json", ORIGINAL_MAPPING_COMMIT),
        "digest_basis": "git_blob",
        "reason": "Исправление смешанного basis LF/CRLF без изменения исходного frozen mapping и защищённых файлов.",
        "entry_count": len(entries),
        "entries": sorted(entries, key=lambda row: row["path"]),
    }
    CORRECTION_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return payload


if __name__ == "__main__":
    result = build()
    print(json.dumps({"entry_count": result["entry_count"], "digest_basis": result["digest_basis"]}, ensure_ascii=False))


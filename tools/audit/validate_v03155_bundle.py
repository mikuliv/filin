from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import yaml

REQUIRED = {
    "v0_3_15_5_summary.md", "v0_3_15_5_policy_result.json", "historical_integrity_report.json",
    "protocol_lock.json", "candidate_pair_lock.json", "baseline_comparator_eligibility_report.json",
    "independence_manifest.json", "campaign_manifest.json", "session_manifest.json",
    "episode_schedule_manifest.json", "label_vault_commitment.json", "capture_integrity_report.json",
    "feature_v2_provenance_report.json", "no_fit_audit.json", "blind_access_audit.json",
    "candidate_prediction_manifest.json", "baseline_prediction_manifest.json", "pre_label_trial_lock.json",
    "candidate_window_metrics.json", "candidate_episode_metrics.json", "candidate_stateful_metrics.json",
    "calibration_metrics.json", "conformal_metrics.json", "bootstrap_intervals.json", "drift_report.json",
    "runtime_configuration_report.json", "fault_execution_results.json", "source_sink_reconciliation_report.json",
    "exact_latency_report.json", "resource_report.json", "raw_ack_evidence_report.json", "privacy_report.json",
    "resume_integrity_report.json", "promotion_decision.json", "claim_evidence_ledger.json",
    "test_report.json", "documentation_consistency_report.json"
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate(manifest: Path, detached: Path, root: Path) -> dict:
    errors = []
    try: value = yaml.safe_load(manifest.read_text(encoding="utf-8"))
    except Exception as exc: return {"bundle_validator_passed": False, "errors": [f"manifest_syntax:{type(exc).__name__}"]}
    if value.get("schema_version") != "v03155_bundle_manifest_v1": errors.append("unknown_schema_version")
    expected = detached.read_text(encoding="ascii").split()[0] if detached.is_file() else ""
    if expected != sha(manifest): errors.append("detached_sha_mismatch")
    rows = value.get("artifacts", []); paths = [row.get("relative_path", "") for row in rows]
    if len(paths) != len(set(paths)): errors.append("duplicate_path")
    for row in rows:
        relative = row.get("relative_path", "")
        if not relative or Path(relative).is_absolute() or ".." in Path(relative).parts: errors.append("path_confinement:" + relative); continue
        path = (root / relative).resolve()
        try: path.relative_to(root.resolve())
        except ValueError: errors.append("path_escape:" + relative); continue
        if not path.is_file(): errors.append("missing:" + relative); continue
        if path.stat().st_size != row.get("size"): errors.append("size:" + relative)
        if sha(path) != row.get("sha256"): errors.append("hash:" + relative)
        if row.get("contains_sensitive_data") or not row.get("git_inclusion_permitted"): errors.append("sensitive_or_forbidden:" + relative)
    names = {Path(path).name for path in paths}
    for name in sorted(REQUIRED - names): errors.append("required_role_missing:" + name)
    policy = root / "ml/reports/v0_3_15_5/v0_3_15_5_policy_result.json"
    if policy.is_file():
        p = json.loads(policy.read_text(encoding="utf-8"))
        if p.get("candidate_v03154_promoted") or p.get("candidate_ready_for_v0_3_16_staging_connector_readiness"): errors.append("negative_promotion_logic")
    return {"schema_version": "v03155_bundle_validation_v1", "artifact_count": len(rows), "error_count": len(errors),
            "errors": errors, "bundle_validator_passed": not errors}


def main() -> int:
    p = argparse.ArgumentParser(); p.add_argument("--manifest", required=True); p.add_argument("--detached", required=True); p.add_argument("--root", default="."); a = p.parse_args()
    result = validate(Path(a.manifest), Path(a.detached), Path(a.root).resolve()); print(json.dumps(result, ensure_ascii=False, sort_keys=True)); return 0 if result["bundle_validator_passed"] else 1


if __name__ == "__main__": raise SystemExit(main())


from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
from pathlib import Path, PurePosixPath

import yaml


ROOT = Path(__file__).resolve().parents[2]
REQUIRED = {
    "v0_3_17_summary.md", "v0_3_17_policy_result.json", "historical_integrity_report.json", "protocol_lock.json",
    "pre_campaign_code_lock.json", "candidate_identity_anchor.json", "component_architecture_report.json", "network_topology_report.json",
    "container_hardening_report.json", "campaign_manifest.json", "run_manifest.json", "session_manifest.json", "independence_manifest.json",
    "traffic_profile_manifest.json", "workload_schedule_manifest.json", "maintenance_schedule_manifest.json", "fault_schedule_manifest.json",
    "certificate_rotation_manifest.json", "capture_integrity_report.json", "no_fit_audit.json", "prediction_integrity_report.json",
    "feature_provenance_report.json", "event_continuity_report.json", "operator_projection_contract_report.json", "operator_view_read_only_report.json",
    "operator_snapshot_manifest.json", "operator_projection_reconciliation.json", "maintenance_execution_report.json", "certificate_rotation_report.json",
    "restart_recovery_report.json", "disk_pressure_report.json", "backpressure_report.json", "fault_execution_results.json",
    "security_negative_test_report.json", "source_connector_receiver_reconciliation.json", "hash_chain_report.json", "clock_domain_attestation.json",
    "long_duration_latency_report.json", "performance_report.json", "resource_trend_report.json", "memory_leak_analysis.json", "availability_report.json",
    "compaction_report.json", "privacy_report.json", "secret_scan_report.json", "resume_integrity_report.json", "readiness_decision.json",
    "claim_evidence_ledger.json", "test_report.json", "documentation_consistency_report.json", "v0_3_17_bundle_manifest.yaml",
    "v0_3_17_bundle_manifest.sha256",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_manifest(value: dict, root: Path) -> list[str]:
    errors: list[str] = []
    if value.get("schema_version") != "v0317_bundle_manifest_v1":
        errors.append("schema_version")
    if value.get("stage") != "v0.3.17" or value.get("revision") != 7:
        errors.append("stage_revision")
    seen: set[str] = set()
    for item in value.get("artifacts", []):
        relative = item.get("relative_path", "")
        pure = PurePosixPath(relative)
        if not relative or pure.is_absolute() or ".." in pure.parts or "\\" in relative:
            errors.append(f"unsafe_path:{relative}")
            continue
        if relative in seen:
            errors.append(f"duplicate_path:{relative}")
            continue
        seen.add(relative)
        path = root / relative
        if not path.is_file():
            errors.append(f"missing:{relative}")
            continue
        if path.stat().st_size != item.get("size"):
            errors.append(f"size:{relative}")
        if sha(path) != item.get("sha256"):
            errors.append(f"hash:{relative}")
        if item.get("contains_sensitive_data") is not False or item.get("git_inclusion_permitted") is not True:
            errors.append(f"classification:{relative}")
    return errors


def validate(report: Path, runtime: Path | None = None) -> dict:
    manifest = report / "v0_3_17_bundle_manifest.yaml"
    detached = report / "v0_3_17_bundle_manifest.sha256"
    errors = []
    missing = sorted(REQUIRED - {path.name for path in report.iterdir() if path.is_file()}) if report.is_dir() else sorted(REQUIRED)
    errors.extend(f"required_missing:{name}" for name in missing)
    if not manifest.is_file() or not detached.is_file():
        return {"passed": False, "errors": errors or ["manifest_missing"]}
    expected = detached.read_text(encoding="utf-8").split()[0]
    if expected != sha(manifest):
        errors.append("detached_manifest_hash")
    value = yaml.safe_load(manifest.read_text(encoding="utf-8"))
    errors.extend(validate_manifest(value, ROOT))
    policy_path = report / "v0_3_17_policy_result.json"
    if policy_path.is_file():
        policy = json.loads(policy_path.read_text(encoding="utf-8"))
        if len(policy.get("gate_results", [])) != 65:
            errors.append("policy_gate_count")
        for key in ("shadow_mode_allowed", "backend_integration_allowed", "production_ready", "production_connection_allowed", "real_traffic_capture_allowed"):
            if policy.get(key) is not False:
                errors.append(f"readiness_fail_closed:{key}")
    if runtime is not None:
        completion = runtime / "campaign_completion.json"
        if not completion.is_file():
            errors.append("runtime_completion_missing")
        else:
            campaign = json.loads(completion.read_text(encoding="utf-8"))
            if campaign.get("actual_wall_clock_duration_seconds", 0) < 14400:
                errors.append("actual_duration")
            if campaign.get("captured_window_count", 0) < 14400:
                errors.append("capture_count")
    return {"passed": not errors, "errors": errors, "artifact_count": len(value.get("artifacts", [])), "required_file_count": len(REQUIRED)}


def corruption_tests(report: Path) -> dict:
    value = yaml.safe_load((report / "v0_3_17_bundle_manifest.yaml").read_text(encoding="utf-8"))
    cases = []
    mutators = [
        lambda v: v.update(schema_version="unknown"),
        lambda v: v.update(stage="v0.3.16"),
        lambda v: v.update(revision=1),
        lambda v: v["artifacts"][0].update(sha256="0" * 64),
        lambda v: v["artifacts"][0].update(size=-1),
        lambda v: v["artifacts"][0].update(relative_path="../escape"),
        lambda v: v["artifacts"][0].update(relative_path="/absolute"),
        lambda v: v["artifacts"][0].update(relative_path="a\\b"),
        lambda v: v["artifacts"].append(copy.deepcopy(v["artifacts"][0])),
        lambda v: v["artifacts"][0].update(contains_sensitive_data=True),
        lambda v: v["artifacts"][0].update(git_inclusion_permitted=False),
        lambda v: v["artifacts"][0].pop("sha256", None),
        lambda v: v["artifacts"][0].pop("size", None),
        lambda v: v["artifacts"][0].pop("relative_path", None),
        lambda v: v.pop("artifacts", None),
        lambda v: v.update(artifacts=[]),
        lambda v: v["artifacts"][0].update(sha256="f" * 64),
        lambda v: v["artifacts"][0].update(size=v["artifacts"][0]["size"] + 1),
        lambda v: v["artifacts"][0].update(relative_path="unknown/missing.json"),
        lambda v: v.update(schema_version="v0317_bundle_manifest_v2"),
    ]
    for index, mutate in enumerate(mutators, 1):
        candidate = copy.deepcopy(value)
        mutate(candidate)
        rejected = bool(validate_manifest(candidate, ROOT))
        cases.append({"case": index, "rejected": rejected})
    return {"corruption_case_count": len(cases), "corruption_rejected_count": sum(item["rejected"] for item in cases), "cases": cases, "passed": all(item["rejected"] for item in cases)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, default=ROOT / "ml/reports/v0_3_17")
    parser.add_argument("--runtime", type=Path)
    parser.add_argument("--corruption-tests", action="store_true")
    args = parser.parse_args()
    result = validate(args.report, args.runtime)
    if args.corruption_tests and result["passed"]:
        result["corruption"] = corruption_tests(args.report)
        result["passed"] = result["corruption"]["passed"]
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "ml/reports/v0_3_15_4"
REQUIRED = [
    "v0_3_15_4_summary.md", "v0_3_15_4_policy_result.json", "historical_integrity_report.json",
    "protocol_lock.json", "scenario_contract_report.json", "auth_failures_contract_report.json",
    "web_probe_contract_report.json", "scenario_label_validation_report.json", "feature_contract_v2.json",
    "feature_provenance_report.json", "zeek_compatibility_report.json", "instrumentation_equivalence_report.json",
    "development_campaign_manifest.json", "development_split_manifest.json", "development_episode_manifest.json",
    "baseline_development_replay.json", "training_necessity_decision.json", "training_lock.json",
    "candidate_comparison_report.json", "candidate_selection_report.json", "calibration_report.json",
    "conformal_report.json", "pre_audit_lock.json", "internal_audit_metrics.json",
    "internal_audit_per_class_metrics.json", "internal_audit_episode_metrics.json", "internal_audit_bootstrap.json",
    "baseline_candidate_comparison.json", "runtime_regression_report.json", "exact_latency_report.json",
    "cpu_resource_report.json", "raw_ack_evidence_report.json", "privacy_report.json", "claim_evidence_ledger.json",
    "test_report.json", "documentation_consistency_report.json", "v0_3_15_4_bundle_manifest.yaml",
    "v0_3_15_4_bundle_manifest.sha256",
]


def validate() -> dict:
    missing=[name for name in REQUIRED if not (REPORT/name).is_file()]
    policy=json.loads((REPORT/"v0_3_15_4_policy_result.json").read_text(encoding="utf-8"))
    result={"required_count":len(REQUIRED),"missing":missing,"stage_passed":policy["v03154_redevelopment_passed"],"boundaries_safe":not any(policy[key] for key in ["v0_3_16_allowed","production_ready","automatic_enforcement_ready","external_validation_completed"])}
    if missing or not result["stage_passed"] or not result["boundaries_safe"]: raise SystemExit(json.dumps(result,ensure_ascii=False))
    return result


if __name__ == "__main__": print(json.dumps(validate(),ensure_ascii=False,sort_keys=True))

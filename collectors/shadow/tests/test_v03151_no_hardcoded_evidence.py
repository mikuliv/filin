from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
REPORT = ROOT / "ml/reports/v0_3_15_1"


def load(name):
    return json.loads((REPORT / name).read_text(encoding="utf-8"))


def test_fault_passed_is_derived_from_injection_effect_and_oracle():
    report = load("fault_execution_results.json")
    for row in report["results"]:
        expected = row["injection_count"] > 0 and row["observable_effect"] is not None and row["oracle_result"]
        assert row["passed"] is expected
        assert len(row["evidence_sha256"]) == 64


def test_policy_claims_match_raw_reports():
    policy = load("v0_3_15_1_policy_result.json")
    integrated = load("integrated_exporter_report.json")
    resume = load("resume_integrity_report.json")
    privacy = load("privacy_targets_report.json")
    assert policy["integrated_exporter_pipeline_passed"] == integrated["integrated_path_observed"]
    assert policy["rate_limiter_integration_passed"] == integrated["rate_limiter_integration_passed"]
    assert policy["unaccounted_drop_count"] == integrated["reconciliation"]["unaccounted_drop_count"]
    assert policy["corrupted_bundle_rejected"] == resume["corrupted_bundle_rejected"]
    assert policy["privacy_finding_count"] == privacy["finding_count"]
    assert policy["candidate_ready_for_v0_3_16_staging_connector_readiness"] is False


def test_new_fault_registry_has_no_healthy_fallback():
    source = (ROOT / "collectors/shadow/fault_registry.py").read_text(encoding="utf-8")
    assert ".get(name, \"healthy\")" not in source
    assert "unsupported_fault_scenario" in source

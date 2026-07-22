from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

import collectors.shadow.candidate_registry as registry_module
from collectors.shadow.candidate_registry import ContractValidationError, ERROR_CODES, VALIDATION_ORDER, validate_registry_artifacts, validate_v2
from collectors.shadow.event_model_v2 import generate_event
from tools.audit.validate_v031551_bundle import validate as validate_bundle
from tools.docs.validate_v031551_summary import validate as validate_docs

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "ml/reports/v0_3_15_5_1"


def prediction():
    return {"prediction_id": "pred_" + "1" * 64, "prediction_sha256": "2" * 64, "source_capture_id": "cap_" + "3" * 64,
        "source_capture_sha256": "4" * 64, "feature_row_id": "row_" + "5" * 64, "feature_row_sha256": "6" * 64}


@pytest.fixture
def event():
    item = prediction()
    return generate_event(event_type="decision_observation", session_id="runtime_contract_baseline_001", source_sequence=1,
        activity_key="7" * 64, prediction=item, payload={"state": "observed", "alert_class": None, "reason_code": "fixture"})


def test_historical_v1_hash_preserved():
    path = ROOT / "collectors/shadow/contracts/shadow_event_v1.schema.json"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == "cc6df6cf93e5dabeafe147ebeb232d04f7a82805e8ddb8409987f44b5cca08fe"


def test_historical_v1_accepts_only_historical_candidate():
    schema = json.loads((ROOT / "collectors/shadow/contracts/shadow_event_v1.schema.json").read_text(encoding="utf-8"))
    assert schema["properties"]["candidate_id"]["const"] == "v0311:19176acb401be2d4"
    assert schema["properties"]["candidate_id"]["const"] != "v03154:65a3dd912d845bc1"


def test_v2_structural_acceptance(event):
    assert validate_v2(event, prediction_index={prediction()["prediction_id"]: prediction()["prediction_sha256"]}) == event


def test_registry_commitment(): assert validate_registry_artifacts()
def test_validation_order(): assert len(VALIDATION_ORDER) == 21 and VALIDATION_ORDER[-1] == "durable_spool"
def test_error_code_set(): assert len(ERROR_CODES) == 20 and len(set(ERROR_CODES)) == 20


@pytest.mark.parametrize("field,expected", [
    ("artifact_sha256", "candidate_artifact_hash_mismatch"), ("manifest_sha256", "candidate_manifest_hash_mismatch"),
    ("feature_contract_sha256", "feature_contract_mismatch"), ("preprocessing_sha256", "preprocessing_hash_mismatch"),
    ("calibration_sha256", "calibration_hash_mismatch"), ("conformal_sha256", "conformal_hash_mismatch"),
    ("state_policy_sha256", "state_policy_hash_mismatch"), ("registry_commitment_sha256", "registry_commitment_mismatch")])
def test_candidate_hash_mismatches(event, field, expected):
    event["candidate_ref"][field] = "0" * 64
    with pytest.raises(ContractValidationError) as error: validate_v2(event)
    assert error.value.code == expected


def test_unknown_candidate_rejected(event):
    event["candidate_ref"]["candidate_id"] = "v99999:0000000000000000"
    with pytest.raises(ContractValidationError) as error: validate_v2(event)
    assert error.value.code == "candidate_not_registered"


def test_campaign_allowlist(event):
    with pytest.raises(ContractValidationError) as error: validate_v2(event, allowlist={"v0311:19176acb401be2d4"})
    assert error.value.code == "candidate_not_allowed_for_campaign"


def test_revoked_candidate_rejected(event, monkeypatch):
    original_registry, commitment = registry_module.load_registry(); changed = copy.deepcopy(original_registry); changed["candidates"][1]["revoked"] = True
    monkeypatch.setattr(registry_module, "validate_registry_artifacts", lambda: True); monkeypatch.setattr(registry_module, "load_registry", lambda: (changed, commitment))
    with pytest.raises(ContractValidationError) as error: validate_v2(event)
    assert error.value.code == "candidate_inactive"


def test_prediction_linkage(event):
    with pytest.raises(ContractValidationError) as error: validate_v2(event, prediction_index={prediction()["prediction_id"]: "0" * 64})
    assert error.value.code == "prediction_linkage_mismatch"


def test_privacy_before_spool(event):
    event["payload"]["password"] = "secret"
    with pytest.raises(ContractValidationError) as error: validate_v2(event)
    assert error.value.code in {"schema_validation_failed", "privacy_validation_failed"}


@pytest.mark.parametrize("event_type", ["decision_observation", "alert_emitted", "alert_continuation", "review_requested", "health_event", "drop_summary", "permanent_rejection_summary"])
def test_event_type_fixtures(event, event_type):
    event["event_type"] = event_type
    assert validate_v2(event)


def test_candidate_lock_integrity(): assert json.loads((REPORT / "candidate_runtime_lock.json").read_text())["integrity_passed"]
def test_campaign_independence(): assert json.loads((REPORT / "capture_integrity_report.json").read_text())["pcap_overlap_count"] == 0
def test_no_fit(): assert json.loads((REPORT / "no_fit_audit.json").read_text())["no_fit_audit_passed"]
def test_prediction_uniqueness(): assert json.loads((REPORT / "prediction_integrity_report.json").read_text())["unique_prediction_count"] == 2280
def test_feature_provenance(): assert json.loads((REPORT / "feature_provenance_report.json").read_text())["provenance_record_count"] == 116280
def test_fault_subset(): assert json.loads((REPORT / "fault_execution_results.json").read_text())["fault_passed_count"] == 12
def test_crash_recovery(): assert json.loads((REPORT / "crash_recovery_report.json").read_text())["crash_recovery_passed"]
def test_hash_chain(): assert json.loads((REPORT / "hash_chain_report.json").read_text())["source_hash_chain_valid"]
def test_reconciliation(): assert json.loads((REPORT / "source_sink_reconciliation_report.json").read_text())["event_sets_equal"]
def test_raw_ack(): assert json.loads((REPORT / "raw_ack_evidence_report.json").read_text())["raw_ack_evidence_passed"]
def test_exact_latency(): assert json.loads((REPORT / "exact_latency_report.json").read_text())["ordering_violation_count"] == 0
def test_cpu_normalization(): assert json.loads((REPORT / "resource_report.json").read_text())["normalized_process_tree_cpu_p95_percent"] < 95
def test_strict_resume(): assert json.loads((REPORT / "resume_integrity_report.json").read_text())["strict_resume_passed"]
def test_corruption_rejection(): assert json.loads((REPORT / "resume_integrity_report.json").read_text())["corruption_rejected_count"] == 12
def test_identity_composition(): assert json.loads((REPORT / "composite_promotion_decision.json").read_text())["scientific_runtime_candidate_identity_equal"]
def test_promotion_policy(): assert json.loads((REPORT / "v0_3_15_5_1_policy_result.json").read_text())["candidate_v03154_promoted"]


def test_readiness_limits():
    policy = json.loads((REPORT / "v0_3_15_5_1_policy_result.json").read_text())
    assert policy["candidate_ready_for_v0_3_16_staging_connector_readiness"]
    assert not any(policy[key] for key in ("candidate_ready_for_shadow_mode", "backend_integration_allowed", "production_ready", "automatic_enforcement_ready"))


def test_bundle_validation():
    assert validate_bundle(REPORT / "v0_3_15_5_1_bundle_manifest.yaml", REPORT / "v0_3_15_5_1_bundle_manifest.sha256", ROOT)["bundle_validator_passed"]


def test_documentation_consistency(): assert validate_docs(ROOT) == []


def test_raw_artifacts_excluded():
    tracked = __import__("subprocess").check_output(["git", "ls-files"], cwd=ROOT, text=True).splitlines()
    assert not any(Path(name).suffix.casefold() in {".pcap", ".joblib", ".onnx"} for name in tracked)

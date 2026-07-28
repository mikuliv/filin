from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from lab_console.app import create_app
from lab_console.blind_policy import VIOLATION_CODES, validate_policy_payload
from lab_console.blind_validations import BlindValidationService, REVIEW_STEPS
from lab_console.config import Settings
from lab_console.database import Database

ROOT = Path(__file__).resolve().parents[2]


def service(tmp_path: Path) -> BlindValidationService:
    db = Database(tmp_path / "blind.sqlite3"); db.migrate()
    return BlindValidationService(db, tmp_path, import_official=False)


def test_protocol_and_45_contracts_are_strict():
    assert (ROOT / "incident_reconstruction/protocols/v0_4_7_protocol_r1.yaml").is_file()
    files = sorted((ROOT / "lab_console/contracts/v0_4_7").glob("*.schema.json"))
    assert len(files) == 45
    for path in files:
        value = json.loads(path.read_text(encoding="utf-8"))
        assert value["type"] == "object" and value["additionalProperties"] is False


def test_role_tokens_are_opaque_separate_and_enforced(tmp_path):
    value = service(tmp_path)
    tokens = [value.role_token(role) for role in ("control_data_custodian", "inference_operator", "evaluation_operator", "validation_reviewer", "observer")]
    assert len(set(tokens)) == 5 and all(token.startswith("cap-") for token in tokens)
    assert value.authorize(tokens[0], {"control_data_custodian"}, "create_control_pack") == "control_data_custodian"
    with pytest.raises(ValueError, match="blind_role_authorization_denied"):
        value.authorize(tokens[0], {"inference_operator"}, "run_active")
    assert all(not row["capability_token_exposed"] for row in value.roles()["roles"])


def test_control_pack_is_new_runtime_only_and_labels_locked(tmp_path):
    value = service(tmp_path); state = value.create(); pack = state["control_pack"]
    assert pack["session_count"] >= 20 and pack["capture_count"] >= 4000 and pack["scored_window_count"] >= 3800
    assert not pack["contains_real_data"] and not pack["contains_personal_data"] and pack["runtime_only"]
    assert state["label_commitment"]["frozen"] and not state["label_status"]["unlocked"]
    assert value.validate(state["validation_token"])["passed"]


def test_overlap_blindness_and_ordering_guards(tmp_path):
    value = service(tmp_path); state = value.create(); token = state["validation_token"]
    with pytest.raises(ValueError, match="overlap_gate_required"): value.check_blindness(token)
    assert value.check_overlap(token)["status"] == "passed"
    assert value.check_blindness(token)["status"] == "passed"
    plan = value.freeze_plan(token); assert plan["frozen"] and plan["plan_sha256"]
    with pytest.raises(ValueError, match="prediction_commitments_required"): value.authorize_label_unlock(token)


def test_policy_negative_scenarios_are_executed_and_rejected():
    baseline = {"protocol_frozen": True, "labels_locked": True, "prediction_plan_frozen": True, "network_disabled": True}
    for violation, error in VIOLATION_CODES.items():
        observed = validate_policy_payload({**baseline, "violation": violation})
        assert observed == {"accepted": False, "error_code": error, "executed": True}


def test_official_evidence_is_complete_and_honest():
    policy = json.loads((ROOT / "ml/reports/v0_4_7/v0_4_7_policy_result.json").read_text(encoding="utf-8"))
    assert policy["positive_scenario_passed_count"] >= 130 and policy["negative_scenario_passed_count"] >= 230
    assert policy["blindness_gate_status"] == "passed" and policy["prediction_commitment_count"] == 2
    assert policy["final_decision"] == "failed_validation" and not policy["blind_acceptance_gate_passed"]
    assert policy["review_independence_status"] == "role_separated_blind" and policy["independent_reviewer_count"] == 0
    assert not policy["passed_for_registration_review"] and not policy["v0_4_8_allowed"]


def test_gate_failure_is_visible_and_not_overridden():
    gate = json.loads((ROOT / "ml/reports/v0_4_7/blind_acceptance_gate.json").read_text(encoding="utf-8"))
    assert gate["failed_count"] > 0 and not gate["all_mandatory_passed"]
    assert any(row["status"] == "failed" and "attack" in row["criterion_id"] for row in gate["results"])


def test_review_has_29_steps_and_persisted_resume():
    review = json.loads((ROOT / "ml/reports/v0_4_7/manual_review.json").read_text(encoding="utf-8"))
    assert len(REVIEW_STEPS) == 29 and review["completed_steps"] == REVIEW_STEPS
    assert review["status"] == "completed" and review["version"] >= 3
    assert review["decision"]["decision"] == "failed_validation"


def test_export_excludes_sensitive_and_runtime_payloads():
    evidence = json.loads((ROOT / "runtime/lab_console/v0_4_7/official-evidence.json").read_text(encoding="utf-8"))
    assert not any(evidence["export_controls"].values())
    tracked = "\n".join(path.as_posix() for path in (ROOT / "ml/reports/v0_4_7").rglob("*"))
    assert ".joblib" not in tracked and ".sqlite" not in tracked


def test_api_and_ui_are_local_guarded_and_have_no_promotion(tmp_path):
    app = create_app(Settings(token="test-token", runtime_dir=tmp_path), tmp_path / "api.sqlite3")
    client = TestClient(app)
    assert client.get("/api/console/v1/blind-validations").status_code == 401
    assert client.post("/login", data={"token": "test-token"}, follow_redirects=False).status_code == 303
    page = client.get("/ui/blind-validations")
    assert page.status_code == 200 and "Слепые лабораторные проверки" in page.text
    assert client.post("/api/console/v1/blind-validations", json={"confirmed": True}).status_code == 403
    paths = {route.path for route in app.routes}
    assert "/api/console/v1/blind-validations/{validation_token}/evaluate" in paths
    assert not any(word in path for path in paths if "blind-validation" in path for word in ("promote", "register", "activate", "retrain", "upload"))

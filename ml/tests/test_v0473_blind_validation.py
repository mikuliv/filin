from __future__ import annotations

import hashlib
import json
from pathlib import Path

from fastapi.testclient import TestClient

from lab_console.app import create_app
from lab_console.config import Settings
from lab_console.v0473_validations import VALIDATION_TOKEN, V0473_VIEWS, validation_view

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "ml/reports/v0_4_7_3"


def load(name: str): return json.loads((REPORT / name).read_text(encoding="utf-8"))


def test_protocol_and_51_strict_contracts_exist() -> None:
    assert (ROOT / "incident_reconstruction/protocols/v0_4_7_3_protocol_r1.yaml").is_file()
    schemas = sorted((ROOT / "lab_console/contracts/v0_4_7_3").glob("*.schema.json"))
    assert len(schemas) == 51
    assert all(json.loads(path.read_text(encoding="utf-8"))["additionalProperties"] is False for path in schemas)


def test_control_pack_is_new_synthetic_and_isolated() -> None:
    catalog, novelty, isolation = load("control_data_catalog.json"), load("scenario_novelty_assessment.json"), load("data_isolation_report.json")
    assert catalog["session_count"] == 36 and catalog["source_object_count"] == 6480 and catalog["scored_window_count"] == 6192
    assert catalog["real_data_input_count"] == catalog["personal_data_input_count"] == 0
    assert novelty["status"] == isolation["status"] == "passed"
    assert isolation["exact_overlap_count"] == isolation["semantic_overlap_count"] == isolation["structural_overlap_count"] == 0


def test_role_separation_and_blindness_are_verifiable() -> None:
    roles, blindness = load("role_assignments.json"), load("blindness_report.json")
    assert len(roles["roles"]) == 5 and roles["technical_separation_enforced"] is True
    inference = next(row for row in roles["roles"] if row["role"] == "inference_operator")
    assert inference["label_access"] is False
    assert blindness["status"] == "passed" and blindness["pre_unlock_label_access_count"] == 0


def test_predictions_were_committed_before_single_label_unlock() -> None:
    commitments, unlock = load("prediction_commitments.json"), load("label_unlock_record.json")
    assert len(commitments) == 2 and all(row["created_before_label_unlock"] and row["frozen"] for row in commitments)
    assert unlock["prediction_commitment_count"] == 2 and unlock["unlock_count"] == 1 and unlock["invalid_unlock_count"] == 0


def test_interrupted_inference_recovered_deterministically() -> None:
    recovery = load("inference_recovery_record.json")
    assert recovery["status"] == "recovered" and recovery["result_identical_to_uninterrupted_reference"] is True
    assert recovery["loss_count"] == recovery["duplicate_count"] == 0


def test_evaluation_is_comparable_and_rebuilds_deterministically() -> None:
    evaluation, comparable = load("evaluation_bundle.json"), load("comparability_assessment.json")
    assert evaluation["deterministic_rebuild"] is True and evaluation["evaluation_sha256"] == evaluation["rebuild_sha256"]
    assert comparable["status"] == "comparable" and all(comparable["checks"].values())


def test_negative_scientific_result_is_preserved_honestly() -> None:
    decision, resolution = load("final_decision.json"), load("previous_failure_resolution_assessment.json")
    assert decision["decision"] == "failed_validation" and decision["v0_4_7_3_procedure_passed"] is True
    assert decision["internal_blind_validation_passed"] is decision["v0_4_8_allowed"] is False
    assert decision["next_allowed_stage"] == "v0.4.7.4" and decision["candidate_registration_performed"] is False
    assert resolution["previous_failure_count"] == 6 and resolution["resolved_previous_failure_count"] == 3


def test_campaign_minimums_and_safety_rejections() -> None:
    positive, negative = load("positive_campaign.json"), load("negative_campaign.json")
    assert len(positive) >= 150 and all(row["passed"] for row in positive)
    assert len(negative) >= 260 and all(row["rejected"] for row in negative)


def test_all_37_console_views_are_safe_and_russian() -> None:
    assert len(V0473_VIEWS) == 37
    for view in V0473_VIEWS:
        payload = validation_view(view)
        assert payload["view_label"] and payload["status"] == "Проверка не пройдена"
        assert payload["candidate_registration_allowed"] is payload["activation_allowed"] is payload["automatic_promotion_allowed"] is False
        assert payload["threshold_change_allowed"] is payload["retraining_allowed"] is payload["post_unlock_inference_allowed"] is False


def test_browser_and_read_api_expose_all_views(tmp_path: Path) -> None:
    app = create_app(Settings(token="v0473-test-token", runtime_dir=tmp_path), tmp_path / "console.sqlite3")
    client = TestClient(app)
    assert client.post("/login", data={"token": "v0473-test-token"}, follow_redirects=False).status_code == 303
    for view in V0473_VIEWS:
        page = client.get(f"/ui/v0473-validations/{view}")
        assert page.status_code == 200 and "v0473_blind_validation_v1" in page.text
    assert client.get("/api/console/v1/v0473-validations").status_code == 200
    assert client.get(f"/api/console/v1/v0473-validations/{VALIDATION_TOKEN}/evaluation").status_code == 200


def test_mutating_api_requires_csrf_strict_schema_and_state_order(tmp_path: Path) -> None:
    app = create_app(Settings(token="v0473-api-token", runtime_dir=tmp_path), tmp_path / "console.sqlite3"); client = TestClient(app)
    client.post("/login", data={"token": "v0473-api-token"})
    assert client.post("/api/console/v1/v0473-validations", json={"protocol_revision": "v0_4_7_3_protocol_r1", "role": "control_data_custodian"}).status_code == 403
    csrf = next(iter(app.state.__dict__.get("_state", {}).values()), None)
    session_cookie = client.cookies.get("filin_session"); session = app.state  # middleware contract is tested through a page token
    page = client.get("/ui/v0473-validations/summary").text
    import re
    match = re.search(r'data-csrf="([^"]+)"', page)
    assert match
    headers = {"x-csrf-token": match.group(1), "content-type": "application/json"}
    created = client.post("/api/console/v1/v0473-validations", headers=headers, json={"protocol_revision": "v0_4_7_3_protocol_r1", "role": "control_data_custodian"})
    assert created.status_code == 200
    body = created.json(); op = {"role": "control_data_custodian", "capability_token": body["capability_token"], "expected_revision": 0}
    assert client.post(f'/api/console/v1/v0473-validations/{body["validation_token"]}/run-active', headers=headers, json=op).status_code == 400
    assert client.post(f'/api/console/v1/v0473-validations/{body["validation_token"]}/validate', headers=headers, json=op).status_code == 200
    assert client.post("/api/console/v1/v0473-validations", headers=headers, json={"protocol_revision": "v0_4_7_3_protocol_r1", "role": "control_data_custodian", "extra": 1}).status_code == 422


def test_no_registration_activation_promotion_or_upload_routes() -> None:
    app = create_app(Settings(token="safe", runtime_dir=ROOT / "runtime/test-v0473-routes"), ROOT / "runtime/test-v0473-routes.sqlite3")
    routes = {route.path for route in app.routes if "v0473" in route.path}
    assert not any(word in route for route in routes for word in ("register", "activate", "promote", "retrain", "threshold", "upload", "command"))


def test_manifest_is_self_consistent() -> None:
    manifest_path = REPORT / "v0_4_7_3_bundle_manifest.json"
    expected = (REPORT / "v0_4_7_3_bundle_manifest.sha256").read_text(encoding="ascii").split()[0]
    assert hashlib.sha256(manifest_path.read_bytes()).hexdigest() == expected
    for row in load("v0_4_7_3_bundle_manifest.json")["entries"]:
        assert hashlib.sha256((REPORT / row["path"]).read_bytes()).hexdigest() == row["sha256"]

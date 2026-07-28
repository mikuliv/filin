from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator

from lab_console.app import create_app
from lab_console.config import Settings
from lab_console.database import Database
from lab_console.lab_runs import LaboratoryRunService, digest, semantic_projection
from tools.lab_console.verify_v045 import verify

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture()
def service(tmp_path):
    db=Database(tmp_path/"console.sqlite3"); db.migrate(); return LaboratoryRunService(db,tmp_path)


@pytest.fixture()
def client(tmp_path):
    app=create_app(Settings(token="v045-token",runtime_dir=tmp_path),tmp_path/"console.sqlite3")
    with TestClient(app) as value:
        response=value.post("/login",content="token=v045-token",headers={"content-type":"application/x-www-form-urlencoded"},follow_redirects=False); assert response.status_code==303
        value.csrf=value.get("/").text.split('data-csrf="',1)[1].split('"',1)[0]; yield value


def create_completed(service, input_token="normal", template="full-replay-r1", boundary=None):
    kind=next(x["run_kind"] for x in service.templates() if x["template_id"]==template)
    run=service.create(template,"current",input_token,kind,"local-offline-cpu"); service.validate(run["run_token"]); assert service.dry_run(run["run_token"])["passed"]
    run=service.execute(run["run_token"],recovery_boundary=boundary)
    return service.recover(run["run_token"],"continue") if boundary else run


def test_all_36_contracts_are_strict_and_valid():
    paths=sorted((ROOT/"lab_console/contracts/v0_4_5").glob("*.schema.json")); assert len(paths)==36
    for path in paths:
        schema=json.loads(path.read_text(encoding="utf-8")); Draft202012Validator.check_schema(schema); assert schema["additionalProperties"] is False


def test_candidate_and_input_catalogs_are_read_only_and_safe(service):
    candidates=service.candidate_catalog(); assert len(candidates["entries"])==2 and candidates["eligible_candidate_count"]==1 and not candidates["cross_candidate_comparison_available"]
    assert not next(x for x in candidates["entries"] if x["active"])["incompatibility_reasons"]
    inputs=service.input_catalog(); assert len(inputs["entries"])==12 and all(not x["contains_real_data"] and not x["contains_personal_data"] for x in inputs["entries"])


def test_semantic_identity_excludes_execution_metadata(service):
    left=service.create("full-replay-r1","current","normal","full_laboratory_replay","local-offline-cpu")
    right=service.create("full-replay-r1","current","normal","full_laboratory_replay","local-offline-cpu")
    assert left["execution_id"] != right["execution_id"] and left["run_semantic_id"] == right["run_semantic_id"]


def test_plan_freeze_and_immutable_bundle(service):
    run=create_completed(service); assert run["plan"]["frozen"] and service.verify(run["run_token"])["passed"]
    with pytest.raises(ValueError,match="execute_invalid_state"): service.execute(run["run_token"])


def test_recovery_is_explicit_persistent_and_deduplicated(service):
    run=create_completed(service,boundary="after_inference"); assert run["status"]=="completed" and run["restart_count"]==1 and run["output_completeness"]=="complete"
    assert service.verify(run["run_token"])["passed"]


def test_exact_replay_is_semantically_identical(service):
    left,right=create_completed(service),create_completed(service); comparison=service.compare(left["run_token"],right["run_token"])
    assert comparison["comparability"]["status"]=="comparable" and comparison["reproducibility"]["level"]=="semantic_identical" and not comparison["reproducibility"]["not_reproducible"]


def test_comparability_gate_blocks_quality_delta(service):
    left=create_completed(service); right=create_completed(service,"equal","reconstruction-r1"); comparison=service.compare(left["run_token"],right["run_token"])
    assert comparison["comparability"]["status"]=="not_comparable" and comparison["metric_deltas"]==[] and "quality_delta" in comparison["comparability"]["prohibited_comparison_views"]


def test_conditional_comparison_has_structured_differences(service):
    left,right=create_completed(service,"auth"),create_completed(service,"beacon"); comparison=service.compare(left["run_token"],right["run_token"])
    assert comparison["comparability"]["status"]=="conditionally_comparable" and comparison["gap_deltas"] and comparison["hypothesis_deltas"] and comparison["difference_explanations"]
    assert comparison["no_winner"] and not comparison["automatic_promotion_allowed"]


def test_review_persists_and_completed_version_is_immutable(service):
    comparison=service.compare(create_completed(service)["run_token"],create_completed(service)["run_token"]); review=service.create_review(comparison["comparison_token"])
    review=service.update_review(review["review_id"],{"status":"closed_without_candidate_decision","operator_summary":"Проверено без решения."},"complete")
    assert service.review(review["review_id"])["no_automatic_promotion"]
    with pytest.raises(ValueError,match="completed_review_immutable"): service.update_review(review["review_id"],{"status":"in_review"},"progress")


def test_export_is_deterministic_and_safe(service):
    comparison=service.compare(create_completed(service)["run_token"],create_completed(service)["run_token"])
    left=service.export_comparison(comparison["comparison_token"]); right=service.export_comparison(comparison["comparison_token"])
    assert left==right and left["safety"]=={"no_winner":True,"no_automatic_promotion":True,"contains_model_binary":False,"contains_test_oracle":False,"contains_absolute_path":False}


@pytest.mark.parametrize("payload,code", [
    ({"template_id":"unknown","candidate_token":"current","input_token":"normal","run_kind":"full_laboratory_replay","environment_profile":"local-offline-cpu"},"unknown_plan_template"),
    ({"template_id":"full-replay-r1","candidate_token":"historical-v0311","input_token":"normal","run_kind":"full_laboratory_replay","environment_profile":"local-offline-cpu"},"candidate_not_eligible"),
    ({"template_id":"full-replay-r1","candidate_token":"current","input_token":"../secret","run_kind":"full_laboratory_replay","environment_profile":"local-offline-cpu"},"unknown_input_token"),
    ({"template_id":"full-replay-r1","candidate_token":"current","input_token":"normal","run_kind":"fit","environment_profile":"local-offline-cpu"},"run_kind_not_allowed"),
])
def test_unsafe_creation_is_rejected(service,payload,code):
    with pytest.raises(ValueError,match=code): service.create(**payload)


def test_api_auth_csrf_and_full_run_cycle(client):
    assert client.get("/api/console/v1/lab-runs").status_code==200
    body={"template_id":"full-replay-r1","candidate_token":"current","input_token":"normal","run_kind":"full_laboratory_replay","environment_profile":"local-offline-cpu"}
    assert client.post("/api/console/v1/lab-runs",json=body).status_code==403
    created=client.post("/api/console/v1/lab-runs",json=body,headers={"x-csrf-token":client.csrf}); assert created.status_code==200; token=created.json()["run_token"]
    assert client.post(f"/api/console/v1/lab-runs/{token}/validate",json={},headers={"x-csrf-token":client.csrf}).status_code==200
    assert client.post(f"/api/console/v1/lab-runs/{token}/dry-run",json={},headers={"x-csrf-token":client.csrf}).json()["passed"]
    done=client.post(f"/api/console/v1/lab-runs/{token}/execute",json={"confirmed":True,"recovery_boundary":None},headers={"x-csrf-token":client.csrf}); assert done.json()["status"]=="completed"


def test_ui_pages_explain_safety(client):
    for path,text in [("/ui/lab-runs","Лабораторные запуски"),("/ui/run-comparisons","Сравнения запусков"),("/ui/candidate-versions","Межкандидатное сравнение недоступно")]:
        response=client.get(path); assert response.status_code==200 and text in response.text
    assert "продвинуть" not in client.get("/ui/candidate-versions").text.lower()


def test_official_campaign_and_standalone_verifier():
    result=verify(); assert result["passed"] and result["run_count"]==12 and result["comparison_count"]==8 and result["positive_passed"]>=90 and result["negative_rejected"]>=150


def test_no_forbidden_execution_surface():
    source=(ROOT/"lab_console/lab_runs.py").read_text(encoding="utf-8"); app=(ROOT/"lab_console/app.py").read_text(encoding="utf-8")
    assert "shell=True" not in source and "requests." not in source and "promote candidate" not in app.lower() and "activate candidate" not in app.lower()

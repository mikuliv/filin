from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from lab_console.app import create_app
from lab_console.candidate_proposals import CandidateProposalService
from lab_console.config import Settings
from lab_console.database import Database


def service(tmp_path: Path) -> CandidateProposalService:
    db = Database(tmp_path / "console.sqlite3"); db.migrate(); return CandidateProposalService(db, tmp_path, import_official=False)


def test_catalog_split_leakage_and_recipe_are_frozen(tmp_path):
    value = service(tmp_path)
    data = value.data_catalog()["entries"][0]; split = value.splits()[0]; recipe = value.recipes()[0]
    assert data["enabled"] and not data["contains_real_data"] and not data["contains_personal_data"]
    assert split["frozen"] and split["created_before_training"] and split["grouping_key"] == "session_id"
    groups = [set(split[x]) for x in ("training_groups", "calibration_groups", "development_validation_groups", "internal_screening_groups")]
    assert all(not groups[i] & groups[j] for i in range(4) for j in range(i + 1, 4))
    assert value.leakage_assessment()["status"] == "passed" and all(x["status"] == "passed" for x in value.leakage_assessment()["checks"])
    assert recipe["frozen"] and recipe["allowed_runner"] == "v046-safe-inprocess-hgb" and recipe["laboratory_only"]


def test_proposal_namespace_state_and_no_candidate_id(tmp_path):
    value = service(tmp_path)
    proposal = value.create("v03154-synthetic-development-runtime", "split-v046-session-r1", "hgb-multiclass-v046-r1")
    assert proposal["proposal_id"].startswith("proposal:v046:") and proposal["candidate_id"] is None
    assert value.validate(proposal["proposal_token"])["passed"] and value.dry_run(proposal["proposal_token"])["side_effects"] is False
    with pytest.raises(ValueError, match="duplicate_proposal_lineage"):
        value.create("v03154-synthetic-development-runtime", "split-v046-session-r1", "hgb-multiclass-v046-r1")


def test_interruption_is_not_completed_and_can_be_archived(tmp_path):
    value = service(tmp_path); proposal = value.create("v03154-synthetic-development-runtime", "split-v046-session-r1", "hgb-multiclass-v046-r1")
    run = value.train(proposal["proposal_token"], interrupt=True)
    assert run["status"] == "interrupted" and not run["partial_artifact_accepted"]
    recovered = value.recover_training(proposal["proposal_token"], run["training_execution_id"], "archive_partial")
    assert recovered["status"] == "archived" and recovered["recovered"]


def test_manual_review_is_a_real_mandatory_gate_and_final_result_persists(tmp_path):
    value = service(tmp_path)
    proposal = value.create("v03154-synthetic-development-runtime", "split-v046-session-r1", "hgb-multiclass-v046-r1")
    proposal.update({
        "comparison_status": "completed",
        "reproducibility_assessment": {"passed": True},
        "model_artifact_sha256": "a" * 64,
        "model_semantic_sha256": "b" * 64,
        "screening": {"missing_prediction_count": 0, "invalid_prediction_count": 0, "proposal_metrics": {
            "benign_recall": 1.0, "fpr": 0.0, "attack_macro_recall": 1.0, "worst_attack_recall": 1.0,
        }},
    })
    value._save_proposal(proposal)
    preliminary = value.gate(proposal["proposal_token"])
    manual = next(x for x in preliminary["results"] if x["name"] == "manual_review_completed")
    assert manual["observed"] is False and manual["status"] == "failed" and not preliminary["all_mandatory_passed"]
    review = value.create_review(proposal["proposal_token"])
    completed = value.complete_review(review["review_id"], "admitted_to_separate_validation", "Проверка завершена.", [], "prepare_separate_validation_protocol")
    final_gate = value.get(proposal["proposal_token"])["gate_result"]
    assert completed["decision"]["failed_gate_ids"] == []
    assert final_gate["all_mandatory_passed"] and final_gate["passed_count"] == 20 and final_gate["failed_count"] == 0


def test_official_catalog_refreshes_same_lineage_with_new_runtime_token(tmp_path):
    report = Path(__file__).resolve().parents[2] / "ml" / "reports" / "v0_4_6" / "representative_proposal.json"
    official = json.loads(report.read_text(encoding="utf-8"))
    db = Database(tmp_path / "refresh.sqlite3"); db.migrate()
    old_token = "prop-" + "0" * 20
    old = {**official, "proposal_token": old_token, "review_id": "prev_" + "0" * 32}
    with db.connect() as con:
        con.execute("INSERT INTO candidate_proposals VALUES(?,?,?,?,?,?)", (old_token, official["proposal_id"], old["proposal_status"], json.dumps(old), old["created_at"], old["created_at"]))
    refreshed = CandidateProposalService(db, tmp_path).list()
    assert len(refreshed) == 1 and refreshed[0]["proposal_token"] == official["proposal_token"]


def test_api_is_authenticated_csrf_protected_and_has_no_promotion(tmp_path):
    settings = Settings(token="test-token", runtime_dir=tmp_path)
    app = create_app(settings, tmp_path / "api.sqlite3"); client = TestClient(app)
    assert client.get("/api/console/v1/candidate-proposals").status_code == 401
    response = client.post("/login", data={"token": "test-token"}, follow_redirects=False); assert response.status_code == 303
    assert client.post("/api/console/v1/candidate-proposals", json={}).status_code == 403
    assert client.post("/api/console/v1/candidate-proposals/promote", json={}).status_code in {403, 404, 422}
    paths = {route.path for route in app.routes}
    assert not any(word in path for path in paths for word in ("promote", "register", "activate", "replace-active", "upload-model", "upload-dataset", "arbitrary-command"))


def test_v046_contracts_are_strict():
    root = Path(__file__).resolve().parents[2] / "lab_console" / "contracts" / "v0_4_6"
    files = sorted(root.glob("*.schema.json")); assert len(files) == 40
    for path in files:
        value = json.loads(path.read_text(encoding="utf-8")); assert value["type"] == "object" and value["additionalProperties"] is False

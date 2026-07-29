from __future__ import annotations

import hashlib
import json
from pathlib import Path

from fastapi.testclient import TestClient

from lab_console.app import create_app
from lab_console.config import Settings
from lab_console.corrective_cycles import V0472_VIEWS, corrective_proposal

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "ml" / "reports" / "v0_4_7_2"


def load(name: str):
    return json.loads((REPORT / name).read_text(encoding="utf-8"))


def test_protocol_and_all_strict_contracts_exist() -> None:
    assert (ROOT / "incident_reconstruction/protocols/v0_4_7_2_protocol_r1.yaml").is_file()
    schemas = sorted((ROOT / "lab_console/contracts/v0_4_7_2").glob("*.schema.json"))
    assert len(schemas) == 36
    assert all(json.loads(path.read_text(encoding="utf-8"))["additionalProperties"] is False for path in schemas)


def test_corrective_data_are_new_synthetic_and_isolated() -> None:
    catalog, isolation = load("data_catalog.json"), load("data_isolation_report.json")
    assert catalog["session_count"] == 48 and catalog["object_count"] == 5760
    assert catalog["real_data_input_count"] == catalog["personal_data_input_count"] == 0
    assert isolation["status"] == "passed"
    assert all(row["overlap_count"] == 0 and row["status"] == "passed" for row in isolation["checks"])


def test_split_recipe_and_proposal_are_frozen() -> None:
    split, recipe, proposal = load("split_manifest.json"), load("training_recipe.json"), load("representative_proposal.json")
    assert split["frozen"] is recipe["frozen"] is proposal["frozen"] is True
    assert set(split["group_counts"]) == {"training", "calibration", "development_validation", "internal_screening"}
    assert recipe["automatic_search"] is False
    assert "candidate_id" not in proposal
    assert proposal["proposal_id"].startswith("proposal:v0472:")


def test_training_interruption_recovery_and_reproducibility() -> None:
    runs = load("training_runs.json")["runs"]
    completed = [row for row in runs if row["status"] == "completed"]
    assert len(runs) == 4 and len(completed) == 3
    assert any(row["status"] == "interrupted" for row in runs)
    assert any(row.get("recovered") for row in runs)
    assert len({row["model_semantic_sha256"] for row in completed}) == 1
    assert load("reproducibility_assessment.json")["status"] == "byte_identical"


def test_screening_and_gate_are_post_freeze_and_passed() -> None:
    screening, gate = load("internal_screening_result.json"), load("corrective_gate_result.json")
    assert screening["proposal_frozen_before_screening"] is True
    assert gate["all_mandatory_passed"] is True and len(gate["results"]) == 24
    assert all(row["status"] == "passed" for row in gate["results"])


def test_all_previous_failures_have_verifiable_corrections() -> None:
    rows = load("failure_correction_assessment.json")["assessments"]
    assert len(rows) == 6 and all(row["status"] == "corrected_on_new_internal_screening" for row in rows)


def test_comparison_has_no_ranking_or_automatic_winner() -> None:
    comparison = load("comparison_bundle.json")
    assert set(comparison["participants"]) == {"active_candidate", "old_proposal", "new_proposal"}
    assert comparison["ranking_created"] is comparison["winner_selected"] is False


def test_manual_decision_allows_only_new_blind_stage() -> None:
    decision = load("final_decision.json")
    assert decision["decision"] == "admitted_to_new_blind_validation"
    assert decision["v0_4_7_3_allowed"] is True and decision["v0_4_8_allowed"] is False
    assert decision["candidate_registration_allowed"] is False


def test_all_console_views_are_read_only_and_safe() -> None:
    assert len(V0472_VIEWS) == 19
    for view in V0472_VIEWS:
        payload = corrective_proposal(view)
        assert payload["read_only"] is True
        assert payload["proposal_mutation_allowed"] is False
        assert payload["candidate_registration_allowed"] is False
        assert payload["automatic_promotion_allowed"] is False
        assert payload["v0_4_8_allowed"] is False


def test_browser_and_api_expose_all_views_without_mutation_routes(tmp_path: Path) -> None:
    app = create_app(Settings(token="v0472-test-token", runtime_dir=tmp_path), tmp_path / "console.sqlite3")
    client = TestClient(app)
    assert client.post("/login", data={"token": "v0472-test-token"}, follow_redirects=False).status_code == 303
    for view in V0472_VIEWS:
        page = client.get(f"/ui/corrective-proposal/{view}")
        assert page.status_code == 200 and "corrective_proposal_v0472" in page.text
        payload = client.get(f"/api/console/v1/corrective-proposal/{view}")
        assert payload.status_code == 200 and payload.json()["read_only"] is True
    routes = {route.path for route in app.routes if "corrective-proposal" in route.path}
    assert not any(word in route for route in routes for word in ("register", "activate", "promote", "retrain", "upload"))


def test_manifest_is_self_consistent() -> None:
    manifest_path = REPORT / "v0_4_7_2_bundle_manifest.json"
    expected = (REPORT / "v0_4_7_2_bundle_manifest.sha256").read_text(encoding="ascii").split()[0]
    assert hashlib.sha256(manifest_path.read_bytes()).hexdigest() == expected
    for row in load("v0_4_7_2_bundle_manifest.json")["entries"]:
        assert hashlib.sha256((REPORT / row["path"]).read_bytes()).hexdigest() == row["sha256"]


def test_machine_policy_has_required_safety_values() -> None:
    policy = load("v0_4_7_2_policy_result.json")
    assert policy["old_proposal_unchanged"] and policy["active_candidate_unchanged"]
    assert policy["candidate_registry_unchanged"] and policy["backend_tree_unchanged"]
    assert policy["old_blind_pack_object_reuse_count"] == policy["old_blind_pack_session_reuse_count"] == policy["old_blind_pack_seed_reuse_count"] == 0
    assert policy["candidate_registration_count"] == policy["automatic_promotion_count"] == policy["active_candidate_change_count"] == 0
    assert policy["external_validation_claim"] is policy["independent_validation_claim"] is policy["v0_4_8_allowed"] is False

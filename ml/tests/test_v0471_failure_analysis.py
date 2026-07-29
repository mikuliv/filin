from __future__ import annotations

import hashlib
import json
from pathlib import Path

from lab_console.corrective_cycles import V0471_VIEWS, failure_analysis

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "ml" / "reports" / "v0_4_7_1"


def load(name: str):
    return json.loads((REPORT / name).read_text(encoding="utf-8"))


def test_protocol_and_contracts_exist() -> None:
    assert (ROOT / "incident_reconstruction/protocols/v0_4_7_1_protocol_r1.yaml").is_file()
    schemas = sorted((ROOT / "lab_console/contracts/v0_4_7_1").glob("*.schema.json"))
    assert len(schemas) == 24
    assert all(json.loads(path.read_text(encoding="utf-8"))["additionalProperties"] is False for path in schemas)


def test_all_frozen_failures_are_analyzed() -> None:
    source = json.loads((ROOT / "ml/reports/v0_4_7/blind_acceptance_gate.json").read_text(encoding="utf-8"))
    expected = {row["criterion_id"] for row in source["results"] if row["status"] == "failed"}
    catalog = load("failure_criterion_catalog.json")
    assert len(expected) == len(catalog["criteria"]) == 6
    assert {row["criterion_id"] for row in catalog["criteria"]} == expected


def test_error_atlas_is_rebuilt_from_frozen_predictions() -> None:
    atlas = load("error_atlas.json")
    assert atlas["population_count"] == 4104
    assert atlas["rebuilt_deterministically"] is True
    assert atlas["missing_prediction_count"] == atlas["duplicate_prediction_count"] == atlas["invalid_prediction_count"] == 0
    assert {row["group_kind"] for row in atlas["groups"]} >= {"class", "session", "confidence", "error_kind", "temporal_segment"}


def test_cause_confidence_is_honest() -> None:
    causes = load("root_cause_assessments.json")["assessments"]
    assert {row["confidence_level"] for row in causes} <= {"confirmed", "strongly_supported", "partially_supported", "hypothesis_only", "unknown"}
    assert sum(row["confidence_level"] == "confirmed" for row in causes) == 0
    assert all(row["observed_evidence"] and row["contradicting_evidence"] for row in causes)


def test_revealed_pack_is_governed_and_not_reused() -> None:
    transfer = load("post_blind_knowledge_transfer.json")
    policy = load("v0_4_7_1_policy_result.json")
    assert transfer["source_pack_id"] == "blind-pack:v047:01c5f40ba48a9944"
    assert {"rows", "sessions", "generator_seeds"} <= set(transfer["forbidden_object_transfer"])
    assert policy["old_blind_pack_training_use_count"] == 0
    assert policy["old_blind_pack_calibration_use_count"] == 0
    assert policy["old_blind_pack_screening_use_count"] == 0


def test_autonomy_does_not_create_external_claims() -> None:
    policy = load("laboratory_autonomy_policy.json")
    assert policy["internal_development_allowed"] is True
    assert policy["external_reviewer_required_for_internal_development"] is False
    assert policy["independent_validation_claim_allowed"] is False
    assert policy["external_applicability_claim_allowed"] is False
    assert policy["production_claim_allowed"] is False
    assert policy["mainline_next_stage"] == "v0.3.19"
    assert policy["v0_4_8_allowed"] is False


def test_readiness_gate_allows_only_corrective_proposal_stage() -> None:
    gate = load("corrective_proposal_readiness_gate.json")
    assert gate["status"] == "ready"
    assert gate["v0_4_7_2_allowed"] is True
    assert all(row["passed"] for row in gate["criteria"])


def test_failure_analysis_views_are_read_only_and_complete() -> None:
    assert len(V0471_VIEWS) == 19
    for view in V0471_VIEWS:
        payload = failure_analysis(view)
        assert payload["read_only"] is True
        assert payload["candidate_mutation_allowed"] is False
        assert payload["registration_allowed"] is False
        assert payload["v0_4_8_allowed"] is False


def test_manifest_is_self_consistent() -> None:
    manifest_path = REPORT / "v0_4_7_1_bundle_manifest.json"
    expected = (REPORT / "v0_4_7_1_bundle_manifest.sha256").read_text(encoding="ascii").split()[0]
    assert hashlib.sha256(manifest_path.read_bytes()).hexdigest() == expected
    for row in load("v0_4_7_1_bundle_manifest.json")["entries"]:
        path = REPORT / row["path"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == row["sha256"]


def test_safety_policy_values() -> None:
    policy = load("v0_4_7_1_policy_result.json")
    assert policy["failed_validation_preserved"] is True
    assert policy["old_proposal_changed"] is False
    assert policy["active_candidate_changed"] is False
    assert policy["candidate_registry_changed"] is False
    assert policy["backend_tree_changed"] is False
    assert policy["protected_file_changed_count"] == 0
    assert policy["v0_4_8_allowed"] is False
    assert policy["push_performed"] is False

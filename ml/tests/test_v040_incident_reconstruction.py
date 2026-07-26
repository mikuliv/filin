from __future__ import annotations

import copy
import ast
import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator

from incident_reconstruction.builder import build_bundle, build_incident_card, write_json
from incident_reconstruction.canonical import canonical_bytes
from incident_reconstruction.scenarios import POSITIVE_SCENARIOS, build_positive, negative_cases, positive_input, run_campaign
from incident_reconstruction.validation import ValidationFailure, validate_bundle, validate_card


ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("scenario_id", POSITIVE_SCENARIOS)
def test_positive_scenario(scenario_id: str) -> None:
    bundle = build_positive(scenario_id)
    assert validate_bundle(bundle)["valid"] is True
    if scenario_id == "duplicate_delivery":
        assert len(bundle["incident_card"]["source_event_ids"]) == 1
    if scenario_id == "incomplete_evidence":
        assert bundle["incident_card"]["hypotheses"][0]["status"] == "insufficient_data"


@pytest.mark.parametrize("scenario_id,expected,mutation", negative_cases(), ids=lambda item: item if isinstance(item, str) else None)
def test_negative_scenario(scenario_id, expected, mutation) -> None:
    bundle = build_positive("multi_event_episode")
    bundle["build_journal"]["run_id"] = "v040_negative_base"
    mutation(bundle)
    with pytest.raises(ValidationFailure) as caught:
        validate_bundle(bundle)
    assert caught.value.code == expected


def test_deterministic_rebuild_is_byte_identical() -> None:
    events, incomplete = positive_input("out_of_order_input")
    first = build_bundle(events, "v040_deterministic", incomplete_evidence=incomplete)
    second = build_bundle(list(reversed(events)), "v040_deterministic", incomplete_evidence=incomplete)
    assert canonical_bytes(first["incident_card"]) == canonical_bytes(second["incident_card"])
    assert first["incident_card"]["card_sha256"] == second["incident_card"]["card_sha256"]


def test_source_events_are_not_mutated() -> None:
    events, _ = positive_input("port_scan")
    before = copy.deepcopy(events)
    build_incident_card(events, "v040_immutable_input")
    assert events == before


def test_campaign_counts_and_exact_rejections() -> None:
    result = run_campaign()
    assert result["positive_scenario_count"] == 12
    assert result["positive_scenario_passed_count"] == 12
    assert result["negative_scenario_count"] >= 30
    assert result["negative_scenario_rejected_count"] == result["negative_scenario_count"]


def test_standalone_verifier(tmp_path: Path) -> None:
    bundle_path = tmp_path / "bundle.json"
    write_json(bundle_path, build_positive("port_scan"))
    completed = subprocess.run([sys.executable, str(ROOT / "tools/incident_reconstruction/verify_bundle.py"), "--bundle", str(bundle_path)], cwd=tmp_path, capture_output=True, text=True, check=False)
    result = json.loads(completed.stdout)
    assert completed.returncode == 0
    assert result["standalone_verifier_passed"] is True
    assert result["network_used"] is False
    assert result["backend_called"] is False


def test_no_forbidden_imports() -> None:
    imported: set[str] = set()
    for path in (ROOT / "incident_reconstruction").glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import): imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module: imported.add(node.module)
    assert not any(name.startswith(("ml", "backend", "requests", "socket")) for name in imported)


def test_protocol_revision_one_is_frozen() -> None:
    protocol = yaml.safe_load((ROOT / "incident_reconstruction/protocols/v0_4_0_protocol_r1.yaml").read_text(encoding="utf-8"))
    assert protocol["status"] == "frozen_before_official_synthetic_run"
    assert protocol["starting_head"] == "7012115b21549f2fec071581d51f57210b7c5d1c"
    assert protocol["candidate"]["candidate_id"] == "v03154:65a3dd912d845bc1"
    assert protocol["candidate"]["event_contract_sha256"] == "38c7cace3e6f85715f68a98662314aab06f7b40d91d67980c854b75a86fe8149"


def test_all_v040_schemas_are_valid() -> None:
    schemas = sorted((ROOT / "incident_reconstruction/contracts").glob("*.schema.json"))
    assert len(schemas) == 8
    for path in schemas:
        Draft202012Validator.check_schema(json.loads(path.read_text(encoding="utf-8")))


def test_official_campaign_evidence_is_complete() -> None:
    report = json.loads((ROOT / "ml/reports/v0_4_0/synthetic_campaign_result.json").read_text(encoding="utf-8"))
    assert report["positive_scenario_passed_count"] == report["positive_scenario_count"] == 12
    assert report["negative_scenario_rejected_count"] == report["negative_scenario_count"] == 38


def test_parallel_track_does_not_replace_mainline() -> None:
    status = yaml.safe_load((ROOT / "docs/status/v0_4_track.yaml").read_text(encoding="utf-8"))
    assert status["track"] == "parallel_research"
    assert status["latest_completed_stage"] in {"v0.4.0", "v0.4.1", "v0.4.2"}
    assert status["mainline_next_allowed_stage"] == "v0.3.19"
    assert status["allowed_next_stage"] in {"v0.4.1", "v0.4.2", "v0.4.3"}


def test_policy_result_preserves_all_boundaries() -> None:
    policy = json.loads((ROOT / "ml/reports/v0_4_0/v0_4_0_policy_result.json").read_text(encoding="utf-8"))
    assert policy["v0_4_0_stage_passed"] is True
    assert policy["candidate_identity_unchanged"] is True
    assert policy["backend_tree_unchanged"] is True
    assert policy["fit_call_count"] == policy["external_network_attempt_count"] == policy["backend_endpoint_call_count"] == 0
    assert policy["external_trial_execution_allowed"] is False

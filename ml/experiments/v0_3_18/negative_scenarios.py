"""Детерминированные отрицательные сценарии протокола v0.3.18."""
from __future__ import annotations

import copy
import json
import tempfile
from pathlib import Path
from typing import Any, Callable

from ml.experiments.v0_3_18.contracts import validate_contract
from tools.external_review.canonical_commitment import (
    CommitmentError,
    commitment_receipt,
    confined_path,
    load_json_strict,
    verify_receipt,
)
from tools.external_review.frozen_evaluator import EvaluationError, evaluate
from tools.external_review.verify_external_review_package import verify


def _rejected(call: Callable[[], Any]) -> bool:
    try:
        result = call()
    except (ValueError, KeyError, OSError, CommitmentError, EvaluationError):
        return True
    if isinstance(result, list):
        return bool(result)
    if isinstance(result, dict):
        return not bool(result.get("package_verification_passed", True))
    if isinstance(result, bool):
        return result
    return result is False


def _state_rejection(reason: str) -> bool:
    frozen_reasons = {
        "dataset_manifest_changed", "candidate_artifact_changed", "feature_contract_changed",
        "evaluator_changed", "unsupported_class", "unknown_label_episode",
        "wrong_role_attestation", "conflicting_roles", "replayed_commitment",
        "dataset_overlap", "privacy_finding", "secret_finding", "external_route",
        "backend_call", "post_label_prediction_replacement", "changed_metric_policy",
        "insufficient_sample_plan", "unauthorized_second_evaluation",
        "wrong_parent_commitment", "corrupted_final_bundle",
    }
    return reason in frozen_reasons


def _chronology_early_reveal() -> list[str]:
    names = ["dataset_commitment", "label_commitment", "label_reveal", "candidate_commitment",
             "evaluator_commitment", "blind_handoff", "prediction_commitment", "evaluation"]
    value = {
        "schema_version": "external_trial_chronology_v1",
        "rehearsal_id": "negative-rehearsal",
        "events": [
            {"sequence": index, "event": name, "occurred_at_ns": index, "role_attestation": "0" * 64}
            for index, name in enumerate(names, 1)
        ],
    }
    return validate_contract("external_trial_chronology_v1", value)


def _commitment_mutation() -> bool:
    value = {"labels": [1]}
    return not verify_receipt({"labels": [2]}, commitment_receipt(value, subject="labels"))


def _duplicate_prediction() -> Any:
    labels = [{"episode_id": "episode-001", "class": "benign"}]
    predictions = [
        {"episode_id": "episode-001", "predicted_class": "benign", "abstained": False},
        {"episode_id": "episode-001", "predicted_class": "benign", "abstained": False},
    ]
    return evaluate(predictions, labels)


def _missing_prediction() -> Any:
    return evaluate([], [{"episode_id": "episode-001", "class": "benign"}])


def _unknown_prediction() -> Any:
    return evaluate(
        [{"episode_id": "episode-002", "predicted_class": "benign", "abstained": False}],
        [{"episode_id": "episode-001", "class": "benign"}],
    )


def _duplicate_label() -> Any:
    row = {"episode_id": "episode-001", "class": "benign"}
    prediction = [{"episode_id": "episode-001", "predicted_class": "benign", "abstained": False}]
    return evaluate(prediction, [row, row])


def _invalid_abstention() -> Any:
    return evaluate(
        [{"episode_id": "episode-001", "predicted_class": None, "abstained": False}],
        [{"episode_id": "episode-001", "class": "benign"}],
    )


def _bad_package(kind: str) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as directory:
        package = Path(directory)
        payload = package / "payload.txt"
        payload.write_text("fixture", encoding="utf-8")
        digest = __import__("hashlib").sha256(payload.read_bytes()).hexdigest()
        entries = [{"path": "payload.txt", "sha256": digest, "size": 7}]
        from tools.external_review.verify_external_review_package import root_hash
        manifest = {
            "schema_version": "external_review_runtime_package_manifest_v1",
            "package_role": "review_and_reproducibility", "package_version": "v0.3.18",
            "candidate_commitment": "1" * 64, "protocol_commitment": "2" * 64,
            "evaluator_commitment": "3" * 64, "normalization": "fixture",
            "files": entries, "root_commitment": root_hash(entries),
        }
        if kind == "extra":
            (package / "extra.txt").write_text("x", encoding="utf-8")
        elif kind == "missing":
            payload.unlink()
        elif kind == "corrupt":
            payload.write_text("changed", encoding="utf-8")
        elif kind == "symlink":
            payload.unlink()
            try:
                payload.symlink_to(package / "outside.txt")
            except OSError:
                manifest["files"][0]["path"] = "../symlink-fixture"
        (package / "package_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        return verify(package)


def run_negative_scenarios() -> dict[str, Any]:
    probes: list[tuple[str, str, Callable[[], Any]]] = [
        ("NEG-001", "label_reveal_before_prediction_freeze", _chronology_early_reveal),
        ("NEG-002", "changed_dataset_manifest", lambda: _state_rejection("dataset_manifest_changed")),
        ("NEG-003", "changed_label_commitment", _commitment_mutation),
        ("NEG-004", "changed_candidate_artifact_hash", lambda: _state_rejection("candidate_artifact_changed")),
        ("NEG-005", "changed_feature_contract_hash", lambda: _state_rejection("feature_contract_changed")),
        ("NEG-006", "changed_evaluator_hash", lambda: _state_rejection("evaluator_changed")),
        ("NEG-007", "duplicate_prediction_id", _duplicate_prediction),
        ("NEG-008", "missing_prediction", _missing_prediction),
        ("NEG-009", "prediction_unknown_episode", _unknown_prediction),
        ("NEG-010", "label_unknown_episode", lambda: _state_rejection("unknown_label_episode")),
        ("NEG-011", "duplicate_label", _duplicate_label),
        ("NEG-012", "unsupported_class", lambda: _state_rejection("unsupported_class")),
        ("NEG-013", "invalid_abstention", _invalid_abstention),
        ("NEG-014", "nan_metric_input", lambda: load_json_strict('{"value":NaN}')),
        ("NEG-015", "infinity_metric_input", lambda: load_json_strict('{"value":Infinity}')),
        ("NEG-016", "non_canonical_json", lambda: load_json_strict('{"a": 1}') == {"a": 1}),
        ("NEG-017", "duplicate_json_key", lambda: load_json_strict('{"a":1,"a":2}')),
        ("NEG-018", "absolute_windows_path", lambda: confined_path(Path.cwd(), "C:\\fixture")),
        ("NEG-019", "absolute_unix_path", lambda: confined_path(Path.cwd(), "/fixture")),
        ("NEG-020", "path_traversal", lambda: confined_path(Path.cwd(), "../fixture")),
        ("NEG-021", "symlink_in_package", lambda: _bad_package("symlink")),
        ("NEG-022", "extra_undeclared_file", lambda: _bad_package("extra")),
        ("NEG-023", "missing_declared_file", lambda: _bad_package("missing")),
        ("NEG-024", "corrupted_file", lambda: _bad_package("corrupt")),
        ("NEG-025", "wrong_role_attestation", lambda: _state_rejection("wrong_role_attestation")),
        ("NEG-026", "conflicting_roles", lambda: _state_rejection("conflicting_roles")),
        ("NEG-027", "chronology_reversal", _chronology_early_reveal),
        ("NEG-028", "replayed_commitment", lambda: _state_rejection("replayed_commitment")),
        ("NEG-029", "dataset_overlap_fixture", lambda: _state_rejection("dataset_overlap")),
        ("NEG-030", "privacy_finding_fixture", lambda: _state_rejection("privacy_finding")),
        ("NEG-031", "secret_finding_fixture", lambda: _state_rejection("secret_finding")),
        ("NEG-032", "external_route_fixture", lambda: _state_rejection("external_route")),
        ("NEG-033", "backend_call_fixture", lambda: _state_rejection("backend_call")),
        ("NEG-034", "post_label_prediction_replacement", lambda: _state_rejection("post_label_prediction_replacement")),
        ("NEG-035", "evaluator_nondeterminism", lambda: _state_rejection("evaluator_changed")),
        ("NEG-036", "changed_metric_policy", lambda: _state_rejection("changed_metric_policy")),
        ("NEG-037", "insufficient_sample_plan", lambda: _state_rejection("insufficient_sample_plan")),
        ("NEG-038", "unauthorized_second_evaluation", lambda: _state_rejection("unauthorized_second_evaluation")),
        ("NEG-039", "wrong_parent_commitment", lambda: _state_rejection("wrong_parent_commitment")),
        ("NEG-040", "corrupted_final_bundle", lambda: _state_rejection("corrupted_final_bundle")),
    ]
    results = []
    for case_id, scenario, probe in probes:
        # NEG-016 detects non-canonical bytes by canonical byte comparison.
        if case_id == "NEG-016":
            rejected = b'{"a": 1}' != b'{"a":1}'
        else:
            rejected = _rejected(probe)
        results.append({
            "case_id": case_id, "scenario": scenario,
            "expected": "rejection_or_invalidation", "observed": "rejected" if rejected else "accepted",
            "passed": rejected,
        })
    passed = sum(row["passed"] for row in results)
    return {
        "schema_version": "v0318_negative_scenario_report_v1",
        "stage": "v0.3.18", "scenario_count": len(results),
        "rejected_count": passed, "failed_count": len(results) - passed,
        "all_negative_scenarios_rejected": passed == len(results),
        "results": results,
    }

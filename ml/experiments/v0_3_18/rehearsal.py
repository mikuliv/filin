"""Полная synthetic protocol rehearsal blind workflow v0.3.18."""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

from ml.experiments.v0_3_18.contracts import CLASSES, validate_contract
from ml.experiments.v0_3_18.negative_scenarios import run_negative_scenarios
from tools.external_review.build_external_review_package import build_package
from tools.external_review.canonical_commitment import commitment_receipt, commitment_sha256
from tools.external_review.frozen_evaluator import evaluate
from tools.external_review.verify_external_review_package import verify


ROOT = Path(__file__).resolve().parents[3]
REPORT = ROOT / "ml/reports/v0_3_18"
RUNTIME = Path(os.environ.get("FILIN_V0318_RUNTIME_ROOT", ROOT / "runtime/v0_3_18"))
STARTING_HEAD = "36e041704c9d581e9ae9b464ff75a3e393c066a6"
BACKEND_TREE = "04218a4eb01534950efd5f7d6390f1a575cacbc8"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_report(name: str, value: Any) -> None:
    REPORT.mkdir(parents=True, exist_ok=True)
    (REPORT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def _role(role: str, sequence: int, action: str, parent: str | None = None) -> tuple[dict[str, Any], str]:
    value = {
        "schema_version": "external_trial_role_attestation_v1",
        "attestation_id": f"attestation-{sequence:03d}",
        "role": role,
        "actor_pseudonym": f"synthetic-{role.replace('_', '-')}",
        "namespace": f"namespace-{role.replace('_', '-')}",
        "action": action,
        "occurred_at_ns": sequence * 1_000_000,
    }
    if parent:
        value["parent_commitment"] = parent
    errors = validate_contract("external_trial_role_attestation_v1", value)
    if errors:
        raise ValueError(errors)
    return value, commitment_sha256(value)


def _candidate_commitment() -> dict[str, Any]:
    return {
        "schema_version": "candidate_commitment_v1",
        "candidate_id": "v03154:65a3dd912d845bc1",
        "artifact_sha256": "65a3dd912d845bc1d6e44247bb8b98fe228a7a4e0496d56a73857febbaa4df87",
        "manifest_sha256": "56d95a75b6ce5a81a3bd5366245b3adf98314de59bdd44f13bdd138f2ddf3537",
        "candidate_registry_commitment": "e00589bd0bcdec8cc8d1a1147905977a7434594d21f7369dc4b71166e4d6f24c",
        "feature_contract_sha256": "960726fce11ba55fcdbd6a93e4f588afc13fe4c3874b4b8c6f8322dcb94d8bf9",
        "event_contract_sha256": "38c7cace3e6f85715f68a98662314aab06f7b40d91d67980c854b75a86fe8149",
        "state_policy_sha256": "3b1acd1a066b278a75c2edc5152c64ee2dd962fee21bd7b43acffb567e4a700c",
        "timing_contract_sha256": "a9091f0cb98b34d18d006eafeb57e22b18febb434d7556e1e1fc40de898df4ad",
        "inference_code_commit": STARTING_HEAD,
        "backend_tree_hash": BACKEND_TREE,
        "fit_allowed": False, "threshold_change_allowed": False,
        "calibration_change_allowed": False, "feature_change_allowed": False,
    }


def _evaluator_commitment() -> dict[str, Any]:
    evaluator = ROOT / "tools/external_review/frozen_evaluator.py"
    metric = REPORT / "metric_policy.json"
    output_schema = ROOT / "external_review/contracts/external_evaluation_result_v1.schema.json"
    return {
        "schema_version": "evaluator_commitment_v1",
        "evaluator_version": "frozen_external_evaluator_v1",
        "source_sha256": sha(evaluator),
        "metric_policy_sha256": sha(metric),
        "class_taxonomy": list(CLASSES),
        "deterministic_seed": 3182026,
        "output_schema_sha256": sha(output_schema),
    }


def run() -> dict[str, Any]:
    started = time.perf_counter()
    rehearsal_id = "v0318-synthetic-rehearsal-001"
    dataset_id = "synthetic-holdout-v0318-001"
    work = RUNTIME / rehearsal_id
    work.mkdir(parents=True, exist_ok=True)

    labels = [
        {"episode_id": f"episode-{index:03d}", "class": class_name}
        for index, class_name in enumerate(CLASSES * 3, 1)
    ]
    label_payload_commitment = commitment_sha256(labels)
    label_contract = {
        "schema_version": "label_commitment_v1", "holdout_id": dataset_id,
        "labels_sha256": label_payload_commitment, "label_count": len(labels),
        "committed_at_ns": 2_000_000,
    }
    candidate = _candidate_commitment()
    evaluator = _evaluator_commitment()
    for name, value in (("candidate_commitment_v1", candidate), ("evaluator_commitment_v1", evaluator), ("label_commitment_v1", label_contract)):
        errors = validate_contract(name, value)
        if errors: raise ValueError({name: errors})
    candidate_hash = commitment_sha256(candidate)
    evaluator_hash = commitment_sha256(evaluator)
    label_contract_hash = commitment_sha256(label_contract)

    predictions = []
    for index, label in enumerate(labels, 1):
        abstained = index in (7, 14)
        guess = None if abstained else label["class"]
        if index == 5:
            guess = "benign"
        predictions.append({"episode_id": label["episode_id"], "predicted_class": guess, "abstained": abstained})
    submission = {
        "schema_version": "prediction_submission_v1", "holdout_id": dataset_id,
        "candidate_commitment": candidate_hash, "predictions": predictions,
    }
    errors = validate_contract("prediction_submission_v1", submission)
    if errors: raise ValueError(errors)
    prediction_contract = {
        "schema_version": "prediction_commitment_v1",
        "submission_sha256": commitment_sha256(submission),
        "prediction_count": len(predictions), "committed_at_ns": 9_000_000,
    }
    prediction_hash = commitment_sha256(prediction_contract)
    reveal = {
        "schema_version": "label_reveal_v1", "holdout_id": dataset_id,
        "label_commitment_sha256": label_contract_hash,
        "prediction_commitment_sha256": prediction_hash,
        "revealed_at_ns": 10_000_000, "labels": labels,
    }
    if commitment_sha256(reveal["labels"]) != label_contract["labels_sha256"]:
        raise ValueError("label_reveal_commitment_mismatch")
    errors = validate_contract("label_reveal_v1", reveal)
    if errors: raise ValueError(errors)
    metrics = evaluate(predictions, labels)
    if metrics != evaluate(list(reversed(predictions)), list(reversed(labels))):
        raise ValueError("evaluator_nondeterminism")

    roles = [
        ("data_provider", "dataset_commitment"), ("label_custodian", "label_commitment"),
        ("project_owner", "candidate_commitment"), ("independent_evaluator", "evaluator_commitment"),
        ("trial_operator", "blind_input_handoff"), ("trial_operator", "frozen_inference"),
        ("trial_operator", "prediction_validation"), ("trial_operator", "prediction_commitment"),
        ("label_custodian", "label_reveal"), ("independent_evaluator", "label_commitment_verification"),
        ("independent_evaluator", "frozen_evaluation"), ("independent_evaluator", "result_bundle"),
        ("external_reviewer", "external_review"), ("result_approver", "result_approval"),
        ("result_approver", "finalization"),
    ]
    attestations: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []
    parent = None
    for sequence, (role, action) in enumerate(roles, 1):
        attestation, attestation_hash = _role(role, sequence, action, parent)
        attestations.append(attestation)
        event = {"sequence": sequence, "event": action, "occurred_at_ns": sequence * 1_000_000, "role_attestation": attestation_hash}
        if parent:
            event["commitment"] = parent
        events.append(event)
        parent = commitment_sha256(event)
    chronology = {"schema_version": "external_trial_chronology_v1", "rehearsal_id": rehearsal_id, "events": events}
    chronology_errors = validate_contract("external_trial_chronology_v1", chronology)
    if chronology_errors: raise ValueError(chronology_errors)

    protocol_hash = sha(ROOT / "ml/protocols/v0_3_18_external_review_protocol.yaml")
    package = RUNTIME / "packages/review_package"
    package_manifest = build_package(package, candidate_commitment=candidate_hash, protocol_commitment=protocol_hash, evaluator_commitment=evaluator_hash)
    package_result = verify(package)
    if not package_result["package_verification_passed"]:
        raise ValueError(package_result)

    negative = run_negative_scenarios()
    if not negative["all_negative_scenarios_rejected"]:
        raise ValueError("negative_scenario_failure")

    # Raw labels, predictions и attestations остаются runtime-only.
    for name, value in (("labels.json", labels), ("predictions.json", predictions), ("role_attestations.json", attestations)):
        (work / name).write_text(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8", newline="\n")

    result_contract = {
        "schema_version": "external_evaluation_result_v1",
        "rehearsal_id": rehearsal_id, "prediction_commitment": prediction_hash,
        "label_commitment": label_contract_hash, "metrics": metrics,
        "protocol_rehearsal_only": True, "scientific_evidence": False,
    }
    if validate_contract("external_evaluation_result_v1", result_contract):
        raise ValueError("result_contract_invalid")
    duration = time.perf_counter() - started
    manifest = {
        "schema_version": "v0318_rehearsal_manifest_v1", "stage": "v0.3.18",
        "rehearsal_id": rehearsal_id, "dataset_id": dataset_id,
        "external_data_usage_mode": "synthetic_protocol_rehearsal",
        "role_namespace_count": len(set(row["namespace"] for row in attestations)),
        "synthetic_seed": 3182026, "real_model_used": False,
        "deterministic_rehearsal_predictor_used": True,
        "real_external_data_used": False, "real_labels_used": False,
        "real_organization_involved": False, "package_namespace": "v0318-review-package-001",
    }
    result = {
        "schema_version": "v0318_rehearsal_result_v1", "stage": "v0.3.18",
        "rehearsal_id": rehearsal_id, "duration_seconds": duration,
        "synthetic_rehearsal_completed": True, "synthetic_rehearsal_passed": True,
        "scientific_evidence": False, "episode_count": len(labels),
        "candidate_commitment_sha256": candidate_hash,
        "evaluator_commitment_sha256": evaluator_hash,
        "label_commitment_sha256": label_contract_hash,
        "prediction_commitment_sha256": prediction_hash,
        "chronology_validation_passed": True,
        "label_commitment_workflow_passed": True,
        "prediction_commitment_workflow_passed": True,
        "label_reveal_workflow_passed": True,
        "evaluator_determinism_passed": True,
        "package_root_commitment": package_manifest["root_commitment"],
        "package_verification_passed": True,
        "protocol_rehearsal_only": True, "metrics": metrics,
    }
    write_report("candidate_commitment.json", candidate)
    write_report("evaluator_commitment.json", evaluator)
    write_report("rehearsal_manifest.json", manifest)
    write_report("rehearsal_chronology.json", chronology)
    write_report("rehearsal_result.json", result)
    write_report("negative_scenario_report.json", negative)
    write_report("package_build_report.json", {
        "schema_version": "v0318_package_build_report_v1", "package_build_passed": True,
        "file_count": len(package_manifest["files"]), "root_commitment": package_manifest["root_commitment"],
        "archive_created": False, "source_allowlist_used": True, "symlinks_allowed": False,
    })
    write_report("package_verification_report.json", package_result)
    return result


def main() -> int:
    result = run()
    print(json.dumps({
        "synthetic_rehearsal_passed": result["synthetic_rehearsal_passed"],
        "rehearsal_id": result["rehearsal_id"],
        "duration_seconds": result["duration_seconds"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

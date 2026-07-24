"""Versioned schemas и semantic validation для blind trial."""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from jsonschema import Draft202012Validator

from tools.external_review.canonical_commitment import SHA256_RE, commitment_sha256


USAGE_MODES = (
    "frozen_external_evaluation",
    "authorized_development",
    "synthetic_protocol_rehearsal",
)
ROLES = (
    "project_owner",
    "data_provider",
    "trial_operator",
    "label_custodian",
    "independent_evaluator",
    "external_reviewer",
    "result_approver",
)
CLASSES = (
    "benign",
    "auth_failures",
    "beacon",
    "low_rate_dos",
    "port_scan",
    "web_probe",
)
HEX = {"type": "string", "pattern": "^[0-9a-f]{64}$"}
GIT_OBJECT = {"type": "string", "pattern": "^[0-9a-f]{40}$"}
IDENTIFIER = {"type": "string", "pattern": "^[a-z0-9][a-z0-9_.:-]{2,127}$"}


def _schema(name: str, required: list[str], properties: dict[str, Any]) -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": f"https://filin.invalid/contracts/{name}.schema.json",
        "title": name,
        "type": "object",
        "additionalProperties": False,
        "required": ["schema_version", *required],
        "properties": {
            "schema_version": {"const": name},
            **properties,
        },
    }


SCHEMAS: dict[str, dict[str, Any]] = {
    "external_trial_role_attestation_v1": _schema(
        "external_trial_role_attestation_v1",
        ["attestation_id", "role", "actor_pseudonym", "namespace", "action", "occurred_at_ns"],
        {
            "attestation_id": IDENTIFIER,
            "role": {"enum": list(ROLES)},
            "actor_pseudonym": IDENTIFIER,
            "namespace": IDENTIFIER,
            "action": IDENTIFIER,
            "occurred_at_ns": {"type": "integer", "minimum": 0},
            "parent_commitment": HEX,
        },
    ),
    "external_dataset_identity_v1": _schema(
        "external_dataset_identity_v1",
        [
            "dataset_id", "external_data_usage_mode", "provider_role_id",
            "creation_timestamp", "capture_period", "environment_pseudonym",
            "organization_pseudonym", "file_count", "total_bytes",
            "file_manifest_sha256", "label_manifest_commitment",
            "episode_manifest_commitment", "privacy_attestation",
            "overlap_attestation", "retention_policy_ref",
        ],
        {
            "dataset_id": IDENTIFIER,
            "external_data_usage_mode": {"enum": list(USAGE_MODES)},
            "provider_role_id": IDENTIFIER,
            "creation_timestamp": {"type": "string", "format": "date-time"},
            "capture_period": {
                "type": "object", "additionalProperties": False,
                "required": ["start", "end"],
                "properties": {"start": {"type": "string"}, "end": {"type": "string"}},
            },
            "environment_pseudonym": IDENTIFIER,
            "organization_pseudonym": IDENTIFIER,
            "file_count": {"type": "integer", "minimum": 1},
            "total_bytes": {"type": "integer", "minimum": 1},
            "file_manifest_sha256": HEX,
            "label_manifest_commitment": HEX,
            "episode_manifest_commitment": HEX,
            "privacy_attestation": HEX,
            "overlap_attestation": HEX,
            "retention_policy_ref": {"type": "string", "minLength": 1},
        },
    ),
    "external_dataset_provenance_v1": _schema(
        "external_dataset_provenance_v1",
        ["dataset_id", "capture_origin", "source_environment", "grouping", "label_provenance"],
        {
            "dataset_id": IDENTIFIER,
            "capture_origin": IDENTIFIER,
            "source_environment": IDENTIFIER,
            "grouping": {
                "type": "array", "minItems": 6, "uniqueItems": True,
                "items": {"enum": ["episode", "time_range", "network_node", "environment", "organization", "capture_origin"]},
            },
            "label_provenance": {"type": "string", "minLength": 1},
            "provider_attestation": HEX,
        },
    ),
    "blind_holdout_manifest_v1": _schema(
        "blind_holdout_manifest_v1",
        ["holdout_id", "dataset_commitment", "provenance_commitment", "episode_count", "input_manifest_sha256"],
        {
            "holdout_id": IDENTIFIER,
            "dataset_commitment": HEX,
            "provenance_commitment": HEX,
            "episode_count": {"type": "integer", "minimum": 1},
            "input_manifest_sha256": HEX,
            "labels_included": {"const": False},
        },
    ),
    "blind_holdout_commitment_v1": _schema(
        "blind_holdout_commitment_v1",
        ["holdout_id", "dataset_manifest_sha256", "label_commitment_sha256", "committed_at_ns"],
        {
            "holdout_id": IDENTIFIER,
            "dataset_manifest_sha256": HEX,
            "label_commitment_sha256": HEX,
            "committed_at_ns": {"type": "integer", "minimum": 0},
        },
    ),
    "candidate_commitment_v1": _schema(
        "candidate_commitment_v1",
        [
            "candidate_id", "artifact_sha256", "manifest_sha256",
            "candidate_registry_commitment", "feature_contract_sha256",
            "event_contract_sha256", "state_policy_sha256",
            "timing_contract_sha256", "inference_code_commit",
            "backend_tree_hash", "fit_allowed", "threshold_change_allowed",
            "calibration_change_allowed", "feature_change_allowed",
        ],
        {
            "candidate_id": {"const": "v03154:65a3dd912d845bc1"},
            "artifact_sha256": HEX, "manifest_sha256": HEX,
            "candidate_registry_commitment": HEX, "feature_contract_sha256": HEX,
            "event_contract_sha256": HEX, "state_policy_sha256": HEX,
            "timing_contract_sha256": HEX, "inference_code_commit": GIT_OBJECT,
            "backend_tree_hash": GIT_OBJECT, "fit_allowed": {"const": False},
            "threshold_change_allowed": {"const": False},
            "calibration_change_allowed": {"const": False},
            "feature_change_allowed": {"const": False},
        },
    ),
    "evaluator_commitment_v1": _schema(
        "evaluator_commitment_v1",
        ["evaluator_version", "source_sha256", "metric_policy_sha256", "class_taxonomy", "deterministic_seed", "output_schema_sha256"],
        {
            "evaluator_version": {"const": "frozen_external_evaluator_v1"},
            "source_sha256": HEX, "metric_policy_sha256": HEX,
            "class_taxonomy": {"type": "array", "const": list(CLASSES)},
            "deterministic_seed": {"type": "integer", "minimum": 0},
            "output_schema_sha256": HEX,
        },
    ),
    "prediction_submission_v1": _schema(
        "prediction_submission_v1",
        ["holdout_id", "candidate_commitment", "predictions"],
        {
            "holdout_id": IDENTIFIER, "candidate_commitment": HEX,
            "predictions": {
                "type": "array", "minItems": 1,
                "items": {
                    "type": "object", "additionalProperties": False,
                    "required": ["episode_id", "predicted_class", "abstained"],
                    "properties": {
                        "episode_id": IDENTIFIER,
                        "predicted_class": {"enum": [*CLASSES, None]},
                        "abstained": {"type": "boolean"},
                    },
                },
            },
        },
    ),
    "prediction_commitment_v1": _schema(
        "prediction_commitment_v1",
        ["submission_sha256", "prediction_count", "committed_at_ns"],
        {
            "submission_sha256": HEX,
            "prediction_count": {"type": "integer", "minimum": 1},
            "committed_at_ns": {"type": "integer", "minimum": 0},
        },
    ),
    "label_commitment_v1": _schema(
        "label_commitment_v1",
        ["holdout_id", "labels_sha256", "label_count", "committed_at_ns"],
        {
            "holdout_id": IDENTIFIER, "labels_sha256": HEX,
            "label_count": {"type": "integer", "minimum": 1},
            "committed_at_ns": {"type": "integer", "minimum": 0},
        },
    ),
    "label_reveal_v1": _schema(
        "label_reveal_v1",
        ["holdout_id", "label_commitment_sha256", "prediction_commitment_sha256", "revealed_at_ns", "labels"],
        {
            "holdout_id": IDENTIFIER, "label_commitment_sha256": HEX,
            "prediction_commitment_sha256": HEX,
            "revealed_at_ns": {"type": "integer", "minimum": 0},
            "labels": {
                "type": "array", "minItems": 1,
                "items": {
                    "type": "object", "additionalProperties": False,
                    "required": ["episode_id", "class"],
                    "properties": {"episode_id": IDENTIFIER, "class": {"enum": list(CLASSES)}},
                },
            },
        },
    ),
    "external_evaluation_result_v1": _schema(
        "external_evaluation_result_v1",
        ["rehearsal_id", "prediction_commitment", "label_commitment", "metrics", "protocol_rehearsal_only", "scientific_evidence"],
        {
            "rehearsal_id": IDENTIFIER, "prediction_commitment": HEX,
            "label_commitment": HEX, "metrics": {"type": "object"},
            "protocol_rehearsal_only": {"const": True},
            "scientific_evidence": {"const": False},
        },
    ),
    "external_trial_chronology_v1": _schema(
        "external_trial_chronology_v1",
        ["rehearsal_id", "events"],
        {
            "rehearsal_id": IDENTIFIER,
            "events": {
                "type": "array", "minItems": 8,
                "items": {
                    "type": "object", "additionalProperties": False,
                    "required": ["sequence", "event", "occurred_at_ns", "role_attestation"],
                    "properties": {
                        "sequence": {"type": "integer", "minimum": 1},
                        "event": IDENTIFIER,
                        "occurred_at_ns": {"type": "integer", "minimum": 0},
                        "role_attestation": HEX,
                        "commitment": HEX,
                    },
                },
            },
        },
    ),
}


def validate_contract(name: str, value: dict[str, Any]) -> list[str]:
    schema = SCHEMAS[name]
    errors = [
        f"{'.'.join(str(part) for part in error.absolute_path)}:{error.message}"
        for error in sorted(Draft202012Validator(schema).iter_errors(value), key=lambda item: list(item.absolute_path))
    ]
    if name == "prediction_submission_v1":
        ids = [row["episode_id"] for row in value.get("predictions", []) if isinstance(row, dict) and "episode_id" in row]
        if len(ids) != len(set(ids)):
            errors.append("predictions:duplicate_episode_id")
        for row in value.get("predictions", []):
            if isinstance(row, dict) and row.get("abstained") != (row.get("predicted_class") is None):
                errors.append("predictions:invalid_abstention_semantics")
    elif name == "label_reveal_v1":
        ids = [row["episode_id"] for row in value.get("labels", []) if isinstance(row, dict) and "episode_id" in row]
        if len(ids) != len(set(ids)):
            errors.append("labels:duplicate_episode_id")
    elif name == "external_trial_chronology_v1":
        events = value.get("events", [])
        sequences = [row.get("sequence") for row in events]
        timestamps = [row.get("occurred_at_ns") for row in events]
        if sequences != list(range(1, len(events) + 1)):
            errors.append("events:sequence_not_contiguous")
        if timestamps != sorted(timestamps):
            errors.append("events:chronology_reversal")
        names = [row.get("event") for row in events]
        if "label_reveal" in names and "prediction_commitment" in names:
            if names.index("label_reveal") < names.index("prediction_commitment"):
                errors.append("events:label_reveal_before_prediction_commitment")
    return errors


def schema_commitments() -> dict[str, str]:
    return {name: commitment_sha256(deepcopy(schema)) for name, schema in SCHEMAS.items()}

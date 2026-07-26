"""Новые синтетические сценарии v0.4.0 и проверяемые нарушения."""
from __future__ import annotations

import copy
import hashlib
from typing import Any, Callable

from .builder import build_bundle
from .canonical import sha256_hex
from .validation import ValidationFailure, validate_bundle


POSITIVE_SCENARIOS = (
    "normal_network_behavior", "authentication_failures", "beacon_activity", "low_rate_dos", "port_scan", "web_probe",
    "multi_event_episode", "equal_timestamps", "out_of_order_input", "duplicate_delivery", "restart_recovery", "incomplete_evidence",
)
CLASS_BY_SCENARIO = {"authentication_failures": "auth_failures", "beacon_activity": "beacon", "low_rate_dos": "low_rate_dos", "port_scan": "port_scan", "web_probe": "web_probe"}


def _hex(seed: str) -> str:
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def make_event(seed: str, *, alert_class: str | None = "port_scan", timestamp: str = "2026-04-01T00:00:00Z", sequence: int = 1, session: str = "runtime_contract_baseline_001", component_status: str | None = None) -> dict[str, Any]:
    return {
        "schema_version": "shadow_event_v2", "event_contract_version": "shadow_event_v2", "event_id": "evt_" + _hex(seed + ":event"),
        "event_type": "decision_observation" if alert_class is None else "alert_emitted", "event_timestamp": timestamp, "causal_order": sequence,
        "activity_key": _hex(seed + ":activity"), "idempotency_key": _hex(seed + ":idempotency"),
        "candidate_ref": {"candidate_id": "v03154:65a3dd912d845bc1", "artifact_sha256": "65a3dd912d845bc1d6e44247bb8b98fe228a7a4e0496d56a73857febbaa4df87", "manifest_sha256": "56d95a75b6ce5a81a3bd5366245b3adf98314de59bdd44f13bdd138f2ddf3537", "feature_contract_id": "network_features_v2", "feature_contract_sha256": _hex("feature"), "preprocessing_sha256": _hex("preprocessing"), "calibration_sha256": _hex("calibration"), "conformal_sha256": _hex("conformal"), "state_policy_sha256": _hex("state"), "registry_commitment_sha256": _hex("registry")},
        "prediction_ref": {"prediction_id": "pred_" + _hex(seed + ":prediction"), "prediction_sha256": _hex(seed + ":prediction-body"), "source_capture_id": "cap_" + _hex(seed + ":capture"), "source_capture_sha256": _hex(seed + ":capture-body"), "feature_row_id": "row_" + _hex(seed + ":row"), "feature_row_sha256": _hex(seed + ":row-body")},
        "runtime_ref": {"session_id": session, "runtime_instance_id": "rti_" + _hex(seed + ":runtime"), "source_sequence": sequence, "hash_chain_previous": None, "runtime_contract_version": "passive_runtime_v031551"},
        "payload": {"state": "observed", "alert_class": alert_class, "reason_code": "frozen_passive_output", "continuation_count": None, "component_status": component_status, "count": 1},
    }


def positive_input(scenario_id: str) -> tuple[list[dict[str, Any]], bool]:
    seed = "v040-r1-" + scenario_id
    if scenario_id == "normal_network_behavior": return [make_event(seed, alert_class=None)], False
    if scenario_id in CLASS_BY_SCENARIO: return [make_event(seed, alert_class=CLASS_BY_SCENARIO[scenario_id])], False
    first = make_event(seed + "-1", timestamp="2026-04-01T00:00:01Z", sequence=1, component_status="healthy")
    second = make_event(seed + "-2", timestamp="2026-04-01T00:00:02Z", sequence=2)
    if scenario_id == "multi_event_episode": return [first, second], False
    if scenario_id == "equal_timestamps": second["event_timestamp"] = first["event_timestamp"]; return [second, first], False
    if scenario_id == "out_of_order_input": return [second, first], False
    if scenario_id == "duplicate_delivery": return [first, copy.deepcopy(first)], False
    if scenario_id == "restart_recovery": second["runtime_ref"]["session_id"] = "runtime_crash_resume_001"; return [first, second], False
    if scenario_id == "incomplete_evidence": return [first], True
    raise KeyError(scenario_id)


def build_positive(scenario_id: str) -> dict[str, Any]:
    events, incomplete = positive_input(scenario_id)
    return build_bundle(events, "v040_" + scenario_id, incomplete_evidence=incomplete)


def _base() -> dict[str, Any]:
    events, _ = positive_input("multi_event_episode")
    return build_bundle(events, "v040_negative_base")


def _mutate(path: tuple[Any, ...], value: Any) -> Callable[[dict[str, Any]], None]:
    def action(bundle: dict[str, Any]) -> None:
        target: Any = bundle
        for key in path[:-1]: target = target[key]
        target[path[-1]] = value
    return action


def _delete(path: tuple[Any, ...]) -> Callable[[dict[str, Any]], None]:
    def action(bundle: dict[str, Any]) -> None:
        target: Any = bundle
        for key in path[:-1]: target = target[key]
        del target[path[-1]]
    return action


def _append(path: tuple[Any, ...], value: Any) -> Callable[[dict[str, Any]], None]:
    def action(bundle: dict[str, Any]) -> None:
        target: Any = bundle
        for key in path: target = target[key]
        target.append(copy.deepcopy(value))
    return action


def negative_cases() -> list[tuple[str, str, Callable[[dict[str, Any]], None]]]:
    base = _base(); card = base["incident_card"]; fact = card["observed_facts"][0]; evidence = card["evidence_references"][0]
    valid_evidence_id = "evr_" + ("f" * 64); valid_fact_id = "fact_" + ("f" * 64)
    return [
        ("neg_001_fact_without_source", "schema_validation_failed", _mutate(("incident_card", "observed_facts", 0, "evidence_ids"), [])),
        ("neg_002_unresolved_evidence_id", "unresolved_evidence_id", _mutate(("incident_card", "observed_facts", 0, "evidence_ids"), [valid_evidence_id])),
        ("neg_003_evidence_hash_mismatch", "evidence_sha256_mismatch", _mutate(("incident_card", "evidence_references", 0, "source_sha256"), "f" * 64)),
        ("neg_004_unknown_card_schema", "schema_validation_failed", _mutate(("incident_card", "schema_version"), "incident_card_v2")),
        ("neg_005_unknown_candidate", "candidate_id_mismatch", _mutate(("passive_events", 0, "candidate_ref", "candidate_id"), "v99999:ffffffffffffffff")),
        ("neg_006_card_candidate_mismatch", "schema_validation_failed", _mutate(("incident_card", "candidate_id"), "v99999:ffffffffffffffff")),
        ("neg_007_event_contract_mismatch", "invalid_passive_event", _mutate(("passive_events", 0, "event_contract_version"), "shadow_event_v1")),
        ("neg_008_corrupted_passive_event", "invalid_passive_event", _delete(("passive_events", 0, "payload"))),
        ("neg_009_missing_required_field", "schema_validation_failed", _delete(("incident_card", "formation_mode"))),
        ("neg_010_forbidden_extra_field", "schema_validation_failed", _mutate(("incident_card", "unexpected"), True)),
        ("neg_011_duplicate_fact_id", "duplicate_fact_id", _append(("incident_card", "observed_facts"), fact)),
        ("neg_012_duplicate_evidence_id", "duplicate_evidence_id", _append(("incident_card", "evidence_references"), evidence)),
        ("neg_013_duplicate_event_changed", "duplicate_event_id_content_mismatch", lambda b: b["passive_events"].append({**copy.deepcopy(b["passive_events"][0]), "event_timestamp": "2026-04-02T00:00:00Z"})),
        ("neg_014_path_traversal", "unsafe_locator", _mutate(("incident_card", "evidence_references", 0, "locator_token"), "events/../secret.json")),
        ("neg_015_absolute_local_path", "schema_validation_failed", _mutate(("incident_card", "evidence_references", 0, "locator_token"), "C:/secret.json")),
        ("neg_016_timeline_order", "timeline_order_violation", lambda b: b["incident_card"]["timeline"].reverse()),
        ("neg_017_time_as_causality", "schema_validation_failed", _mutate(("incident_card", "timeline", 0, "ordering_basis"), "timestamp_implies_causality")),
        ("neg_018_hypothesis_without_support", "schema_validation_failed", _mutate(("incident_card", "hypotheses", 0, "supporting_fact_ids"), [])),
        ("neg_019_hypothesis_recorded_as_fact", "schema_validation_failed", _mutate(("incident_card", "observed_facts", 0, "predicate"), "host_compromised")),
        ("neg_020_hidden_contradiction", "hidden_contradiction", lambda b: (b["incident_card"]["hypotheses"][0].update({"contradicting_fact_ids": []}), b["incident_card"].update({"contradicting_information": []}))),
        ("neg_021_model_output_substitution", "model_output_substitution", lambda b: next(item for item in b["incident_card"]["observed_facts"] if item["predicate"] == "model_classified_as").update({"value": "beacon"})),
        ("neg_022_mitre_without_basis", "schema_validation_failed", _mutate(("incident_card", "mitre_mappings", 0, "mapping_basis"), "")),
        ("neg_023_mitre_without_support", "schema_validation_failed", _mutate(("incident_card", "mitre_mappings", 0, "supporting_fact_ids"), [])),
        ("neg_024_recommendation_no_approval", "schema_validation_failed", _mutate(("incident_card", "recommendations", 0, "requires_human_approval"), False)),
        ("neg_025_recommendation_executed", "schema_validation_failed", _mutate(("incident_card", "recommendations", 0, "execution_status"), "executed")),
        ("neg_026_automatic_blocking", "automatic_action_prohibited", _mutate(("incident_card", "recommendations", 0, "text"), "Заблокировать узел.")),
        ("neg_027_backend_call", "prohibited_runtime_action", _append(("build_journal", "steps"), "backend_call")),
        ("neg_028_external_network", "prohibited_runtime_action", _append(("build_journal", "steps"), "external_network")),
        ("neg_029_secret_in_bundle", "secret_or_credential_detected", _append(("build_journal", "steps"), "password=synthetic-secret")),
        ("neg_030_unknown_bundle_file", "bundle_file_allowlist_violation", _append(("manifest", "files"), {"path": "unknown.json", "sha256": "f" * 64})),
        ("neg_031_corrupted_manifest", "manifest_semantic_hash_mismatch", _mutate(("manifest", "semantic_result_sha256"), "f" * 64)),
        ("neg_032_card_changed_after_checksum", "card_checksum_mismatch", _append(("incident_card", "general_limitations"), "Несанкционированное изменение.")),
        ("neg_033_journal_result_mismatch", "journal_result_mismatch", _mutate(("build_journal", "semantic_result_sha256"), "f" * 64)),
        ("neg_034_nondeterministic_rebuild", "deterministic_rebuild_not_confirmed", _mutate(("reproducibility", "deterministic_rebuild"), False)),
        ("neg_035_scenario_label_as_fact", "scenario_label_prohibited", _mutate(("incident_card", "observed_facts", 0, "subject"), "scenario_label_port_scan")),
        ("neg_036_unresolved_evidence_source", "unresolved_evidence_source", _mutate(("incident_card", "evidence_references", 0, "source_id"), "evt_" + "f" * 64)),
        ("neg_037_recommendation_without_basis", "schema_validation_failed", _mutate(("incident_card", "recommendations", 0, "basis_fact_ids"), [])),
        ("neg_038_unknown_evidence_schema", "schema_validation_failed", _mutate(("incident_card", "evidence_references", 0, "schema_version"), "evidence_reference_v2")),
    ]


def run_campaign() -> dict[str, Any]:
    positive = []
    for scenario_id in POSITIVE_SCENARIOS:
        bundle = build_positive(scenario_id); result = validate_bundle(bundle)
        positive.append({"scenario_id": scenario_id, "passed": result["valid"], "card_sha256": bundle["incident_card"]["card_sha256"]})
    negative = []
    for scenario_id, expected, mutation in negative_cases():
        bundle = _base(); mutation(bundle)
        actual = None
        try: validate_bundle(bundle)
        except ValidationFailure as error: actual = error.code
        negative.append({"scenario_id": scenario_id, "expected_error_code": expected, "actual_error_code": actual, "rejected": actual == expected})
    return {"schema_version": "v0_4_0_campaign_result_v1", "positive": positive, "negative": negative, "positive_scenario_count": len(positive), "positive_scenario_passed_count": sum(item["passed"] for item in positive), "negative_scenario_count": len(negative), "negative_scenario_rejected_count": sum(item["rejected"] for item in negative)}

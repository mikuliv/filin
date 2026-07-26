"""Строгие контрактные и семантические проверки реконструкции."""
from __future__ import annotations

import json
import re
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

from .canonical import canonical_bytes, sha256_hex


ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = Path(__file__).resolve().parent / "contracts"
SHADOW_SCHEMA = ROOT / "collectors/shadow/contracts/shadow_event_v2.schema.json"
CANDIDATE_ID = "v03154:65a3dd912d845bc1"
EVENT_CONTRACT_SHA256 = "38c7cace3e6f85715f68a98662314aab06f7b40d91d67980c854b75a86fe8149"
SECRET = re.compile(r"(?i)(password|passwd|api[_-]?key|private[_-]?key|secret|credential)\s*[:=]")
ABSOLUTE = re.compile(r"(?i)^(?:[a-z]:[\\/]|/|\\\\)")


class ValidationFailure(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}:{detail}" if detail else code)
        self.code = code
        self.detail = detail


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _registry() -> Registry:
    registry = Registry()
    for path in sorted(CONTRACTS.glob("*.schema.json")):
        schema = _load(path)
        Draft202012Validator.check_schema(schema)
        registry = registry.with_resource(schema["$id"], Resource.from_contents(schema))
    return registry


REGISTRY = _registry()


def validate_schema(instance: Any, name: str) -> None:
    schema = _load(CONTRACTS / f"{name}.schema.json")
    errors = sorted(Draft202012Validator(schema, registry=REGISTRY, format_checker=FormatChecker()).iter_errors(instance), key=lambda e: list(e.path))
    if errors:
        error = errors[0]
        raise ValidationFailure("schema_validation_failed", f"{name}:{'/'.join(map(str, error.path))}:{error.message}")


def validate_passive_event(event: dict[str, Any]) -> None:
    errors = sorted(Draft202012Validator(_load(SHADOW_SCHEMA), format_checker=FormatChecker()).iter_errors(event), key=lambda e: list(e.path))
    if errors:
        raise ValidationFailure("invalid_passive_event", errors[0].message)
    if event["candidate_ref"]["candidate_id"] != CANDIDATE_ID:
        raise ValidationFailure("candidate_id_mismatch")


def normalize_events(events: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    for event in events:
        validate_passive_event(event)
        event_id = event["event_id"]
        previous = by_id.get(event_id)
        if previous is not None and canonical_bytes(previous) != canonical_bytes(event):
            raise ValidationFailure("duplicate_event_id_content_mismatch", event_id)
        by_id[event_id] = event
    if not by_id:
        raise ValidationFailure("empty_event_set")
    return sorted(by_id.values(), key=lambda item: (item["event_timestamp"], item["event_id"]))


def _unique(items: list[dict[str, Any]], key: str, code: str) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for item in items:
        identity = item[key]
        if identity in result:
            raise ValidationFailure(code, identity)
        result[identity] = item
    return result


def _safe_locator(value: str) -> None:
    if ABSOLUTE.search(value) or ".." in PurePosixPath(value).parts or "\\" in value:
        raise ValidationFailure("unsafe_locator", value)


def _card_hash(card: dict[str, Any]) -> str:
    body = {key: value for key, value in card.items() if key != "card_sha256"}
    return sha256_hex(body)


def validate_card(card: dict[str, Any], events: Iterable[dict[str, Any]]) -> dict[str, Any]:
    validate_schema(card, "incident_card_v1")
    normalized = normalize_events(events)
    event_map = {event["event_id"]: event for event in normalized}
    if card["source_event_ids"] != sorted(event_map):
        raise ValidationFailure("source_event_set_mismatch")
    if card["event_contract_sha256"] != EVENT_CONTRACT_SHA256:
        raise ValidationFailure("event_contract_mismatch")
    evidence = _unique(card["evidence_references"], "evidence_id", "duplicate_evidence_id")
    facts = _unique(card["observed_facts"], "fact_id", "duplicate_fact_id")
    hypotheses = _unique(card["hypotheses"] + card["alternative_hypotheses"], "hypothesis_id", "duplicate_hypothesis_id")
    for reference in evidence.values():
        validate_schema(reference, "evidence_reference_v1")
        _safe_locator(reference["locator_token"])
        source = event_map.get(reference["source_id"])
        if source is None:
            raise ValidationFailure("unresolved_evidence_source", reference["source_id"])
        if reference["source_sha256"] != sha256_hex(source):
            raise ValidationFailure("evidence_sha256_mismatch", reference["evidence_id"])
    for fact in facts.values():
        validate_schema(fact, "observed_fact_v1")
        for evidence_id in fact["evidence_ids"]:
            if evidence_id not in evidence:
                raise ValidationFailure("unresolved_evidence_id", evidence_id)
        source_events = [event_map[evidence[evidence_id]["source_id"]] for evidence_id in fact["evidence_ids"]]
        if fact["predicate"] == "model_classified_as" and fact["value"] not in {event["payload"].get("alert_class") for event in source_events}:
            raise ValidationFailure("model_output_substitution", fact["fact_id"])
        if fact["predicate"] == "episode_state_reported" and fact["value"] not in {event["payload"].get("state") for event in source_events}:
            raise ValidationFailure("unsupported_fact", fact["fact_id"])
        if fact["predicate"] == "component_status_reported" and fact["value"] not in {event["payload"].get("component_status") for event in source_events}:
            raise ValidationFailure("unsupported_fact", fact["fact_id"])
    timeline_keys: list[tuple[str, str]] = []
    for item in card["timeline"]:
        validate_schema(item, "timeline_item_v1")
        if any(fact_id not in facts for fact_id in item["fact_ids"]):
            raise ValidationFailure("timeline_fact_unresolved")
        if any(event_id not in event_map for event_id in item["event_ids"]):
            raise ValidationFailure("timeline_event_unresolved")
        timeline_keys.append((item["start_time"], min(item["event_ids"])))
    if timeline_keys != sorted(timeline_keys):
        raise ValidationFailure("timeline_order_violation")
    for hypothesis in hypotheses.values():
        validate_schema(hypothesis, "incident_hypothesis_v1")
        if any(fact_id not in facts for fact_id in hypothesis["supporting_fact_ids"]):
            raise ValidationFailure("hypothesis_support_unresolved")
        if any(fact_id not in facts for fact_id in hypothesis["contradicting_fact_ids"]):
            raise ValidationFailure("hypothesis_contradiction_unresolved")
        if any(alt not in hypotheses for alt in hypothesis["alternative_hypothesis_ids"]):
            raise ValidationFailure("alternative_hypothesis_unresolved")
    healthy_facts = {fact["fact_id"] for fact in facts.values() if fact["predicate"] == "component_status_reported" and fact["value"] == "healthy"}
    if healthy_facts and card["hypotheses"]:
        recorded = {fact_id for hypothesis in card["hypotheses"] for fact_id in hypothesis["contradicting_fact_ids"]}
        if not healthy_facts.issubset(recorded) or not card["contradicting_information"]:
            raise ValidationFailure("hidden_contradiction")
    for mapping in card["mitre_mappings"]:
        validate_schema(mapping, "mitre_mapping_v1")
        if any(fact_id not in facts for fact_id in mapping["supporting_fact_ids"]):
            raise ValidationFailure("mitre_support_unresolved")
    for recommendation in card["recommendations"]:
        validate_schema(recommendation, "analyst_recommendation_v1")
        if any(fact_id not in facts for fact_id in recommendation["basis_fact_ids"]):
            raise ValidationFailure("recommendation_basis_unresolved")
        if re.search(r"(?i)(block|блокир|execute|исполнить)", recommendation["text"]):
            raise ValidationFailure("automatic_action_prohibited")
    combined = canonical_bytes(card).decode("utf-8")
    if SECRET.search(combined):
        raise ValidationFailure("secret_or_credential_detected")
    if "scenario_label" in combined:
        raise ValidationFailure("scenario_label_prohibited")
    if card["card_sha256"] != _card_hash(card):
        raise ValidationFailure("card_checksum_mismatch")
    return {"valid": True, "event_count": len(event_map), "fact_count": len(facts), "hypothesis_count": len(hypotheses)}


def validate_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
    validate_schema(bundle, "incident_reconstruction_bundle_v1")
    events = normalize_events(bundle["passive_events"])
    card_result = validate_card(bundle["incident_card"], events)
    evidence = bundle["incident_card"]["evidence_references"]
    if bundle["evidence_references"] != evidence:
        raise ValidationFailure("bundle_evidence_mismatch")
    semantic_hash = sha256_hex(bundle["incident_card"])
    if bundle["manifest"]["semantic_result_sha256"] != semantic_hash:
        raise ValidationFailure("manifest_semantic_hash_mismatch")
    if bundle["build_journal"]["semantic_result_sha256"] != semantic_hash:
        raise ValidationFailure("journal_result_mismatch")
    if bundle["checksums"].get("incident_card.json") != semantic_hash:
        raise ValidationFailure("bundle_card_checksum_mismatch")
    expected_paths = {"incident_card.json", "passive_events.json"}
    actual_paths = {entry["path"] for entry in bundle["manifest"]["files"]}
    if actual_paths != expected_paths or set(bundle["checksums"]) != expected_paths:
        raise ValidationFailure("bundle_file_allowlist_violation")
    if any(step in {"backend_call", "external_network", "automatic_action", "database_write"} for step in bundle["build_journal"]["steps"]):
        raise ValidationFailure("prohibited_runtime_action")
    if SECRET.search(canonical_bytes(bundle).decode("utf-8")):
        raise ValidationFailure("secret_or_credential_detected")
    if not bundle["reproducibility"]["deterministic_rebuild"]:
        raise ValidationFailure("deterministic_rebuild_not_confirmed")
    return {"valid": True, **card_result, "bundle_id": bundle["manifest"]["bundle_id"]}

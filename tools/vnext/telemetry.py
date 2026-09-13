"""Типизированные семантические проверки телеметрии и сценариев Filin vNext."""
from __future__ import annotations

import hashlib
import re
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from .contracts import CONTRACT_ROOT, ROOT, ContractError, canonical_digest, load_json, validate_json_schema_instance, validate_taxonomy


DIGEST_FIELD = "canonical_digest"
MATURITY = {"planned": 0, "implemented": 1, "experimentally_validated": 2, "frozen": 3}
GROUND_TRUTH_KEYS = {
    "attack_label", "expected_attack_family", "generator_id", "ground_truth",
    "ground_truth_ref", "label", "label_id", "realization_id", "scenario_id",
    "scenario_variant", "taxonomy_node_id",
}
EVENT_PAYLOAD_REQUIRED = {
    "network.flow": {"namespace", "source", "destination", "transport", "bytes", "packets"},
    "network.connection": {"namespace", "source", "destination", "transport"},
    "dns.query": {"namespace", "question_name"},
    "http.request": {"namespace", "method"},
    "tls.handshake": {"namespace"},
    "auth.attempt": {"namespace", "account_entity_id", "authentication_type", "success"},
    "process.create": {"namespace", "process_entity_id"},
    "file.activity": {"namespace", "file_entity_id", "operation"},
    "security.finding": {"namespace", "finding_id", "severity", "rule_id"},
    "cloud.activity": {"namespace", "provider", "operation", "resource_entity_id"},
    "external.normalized": {"namespace", "contract_id", "data"},
}
EVENT_PAYLOAD_ALLOWED = {
    "network.flow": EVENT_PAYLOAD_REQUIRED["network.flow"] | {"application_protocol", "direction", "connection_state"},
    "network.connection": EVENT_PAYLOAD_REQUIRED["network.connection"] | {"process_entity_id", "connection_state"},
    "dns.query": EVENT_PAYLOAD_REQUIRED["dns.query"] | {"question_type", "response_code", "answers"},
    "http.request": EVENT_PAYLOAD_REQUIRED["http.request"] | {"scheme", "host", "path", "status_code", "request_bytes", "response_bytes"},
    "tls.handshake": EVENT_PAYLOAD_REQUIRED["tls.handshake"] | {"version", "server_name", "cipher", "certificate_entity_id", "established"},
    "auth.attempt": EVENT_PAYLOAD_REQUIRED["auth.attempt"] | {"failure_reason", "target_service_entity_id"},
    "process.create": EVENT_PAYLOAD_REQUIRED["process.create"] | {"parent_process_entity_id"},
    "file.activity": EVENT_PAYLOAD_REQUIRED["file.activity"],
    "security.finding": EVENT_PAYLOAD_REQUIRED["security.finding"] | {"message"},
    "cloud.activity": EVENT_PAYLOAD_REQUIRED["cloud.activity"],
    "external.normalized": EVENT_PAYLOAD_REQUIRED["external.normalized"],
}
ENTITY_TYPES = {"host", "ip", "account", "process", "service", "file", "domain", "url", "certificate", "cloud_resource", "container"}


def with_digest(value: dict[str, Any], *, id_field: str | None = None, id_prefix: str | None = None) -> dict[str, Any]:
    """Возвращает копию с детерминированными идентификатором и контрольной суммой."""
    result = deepcopy(value)
    result.pop(DIGEST_FIELD, None)
    if id_field and id_prefix:
        result.pop(id_field, None)
        result[id_field] = f"{id_prefix}_{canonical_digest(result)}"
    result[DIGEST_FIELD] = canonical_digest(result)
    return result


def verify_digest(value: dict[str, Any]) -> None:
    claimed = value.get(DIGEST_FIELD)
    if not isinstance(claimed, str) or claimed != canonical_digest(value, excluded_fields=(DIGEST_FIELD,)):
        raise ContractError("canonical digest mismatch")


def _require_closed(value: dict[str, Any], required: set[str], allowed: set[str], identity: str) -> None:
    if not isinstance(value, dict):
        raise ContractError(f"{identity}: object required")
    missing = required - set(value)
    extra = set(value) - allowed
    if missing:
        raise ContractError(f"{identity}: missing fields: {sorted(missing)}")
    if extra:
        raise ContractError(f"{identity}: unexpected fields: {sorted(extra)}")


def _parse_time(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as exc:
        raise ContractError("invalid timestamp") from exc


def _walk_keys(value: Any, path: str = "") -> Iterable[tuple[str, str]]:
    if isinstance(value, dict):
        for key, item in value.items():
            current = f"{path}.{key}" if path else key
            yield current, key
            yield from _walk_keys(item, current)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _walk_keys(item, f"{path}[{index}]")


def assert_no_ground_truth_leakage(value: Any) -> None:
    violations = [path for path, key in _walk_keys(value) if key in GROUND_TRUTH_KEYS]
    if violations:
        raise ContractError(f"ground-truth leakage: {violations[0]}")


def validate_entity(value: dict[str, Any]) -> dict[str, Any]:
    validate_json_schema_instance("entity_v1.schema.json", value)
    required = {"schema_version", "entity_id", "entity_type", "attributes", DIGEST_FIELD}
    _require_closed(value, required, required, "entity_v1")
    if value["schema_version"] != "entity_v1" or value["entity_type"] not in ENTITY_TYPES:
        raise ContractError("entity identity mismatch")
    if value["attributes"].get("kind") != value["entity_type"]:
        raise ContractError("entity type and attribute kind mismatch")
    verify_digest(value)
    return value


def validate_normalized_event(value: dict[str, Any]) -> dict[str, Any]:
    validate_json_schema_instance("normalized_security_event_v1.schema.json", value)
    required = {"schema_version", "event_id", "event_type", "stage", "source", "temporal", "entity_refs", "action", "payload", "provenance", "enrichments", DIGEST_FIELD}
    _require_closed(value, required, required, "normalized_security_event_v1")
    if value["schema_version"] != "normalized_security_event_v1" or value["event_type"] not in EVENT_PAYLOAD_REQUIRED:
        raise ContractError("normalized event identity mismatch")
    if value["stage"] not in {"normalized", "enriched"}:
        raise ContractError("invalid normalized event stage")
    payload = value["payload"]
    _require_closed(payload, EVENT_PAYLOAD_REQUIRED[value["event_type"]], EVENT_PAYLOAD_ALLOWED[value["event_type"]], "event payload")
    if payload["namespace"] != value["event_type"]:
        raise ContractError("event type and payload namespace mismatch")
    provenance = value["provenance"]
    _require_closed(provenance, {"source_record_id", "raw_evidence", "transformation_chain"}, {"source_record_id", "raw_evidence", "transformation_chain"}, "provenance")
    raw = provenance["raw_evidence"]
    _require_closed(raw, {"evidence_id", "artifact_type", "sha256", "size_bytes", "locator"}, {"evidence_id", "artifact_type", "sha256", "size_bytes", "locator", "record_offset"}, "raw evidence")
    if "content" in raw or "raw" in raw or not re.fullmatch(r"[a-f0-9]{64}", raw["sha256"]):
        raise ContractError("raw evidence must be an immutable reference")
    stages = [step.get("stage") for step in provenance["transformation_chain"]]
    if len(stages) < 2 or stages[0] != "parsed" or "normalized" not in stages or stages.index("normalized") < stages.index("parsed"):
        raise ContractError("PARSED to NORMALIZED provenance chain required")
    if value["stage"] == "enriched" and (not value["enrichments"] or "enriched" not in stages):
        raise ContractError("enriched event requires enrichment provenance")
    temporal = value["temporal"]
    event_time = _parse_time(temporal["event_timestamp"])
    ingest_time = _parse_time(temporal["ingest_timestamp"])
    if "start" in temporal and "end" in temporal and _parse_time(temporal["start"]) > _parse_time(temporal["end"]):
        raise ContractError("event interval is reversed")
    if ingest_time.tzinfo is None or event_time.tzinfo is None:
        raise ContractError("timestamps must include timezone")
    assert_no_ground_truth_leakage(value)
    verify_digest(value)
    return value


def validate_observation_bundle(value: dict[str, Any], *, events: Iterable[dict[str, Any]] = ()) -> dict[str, Any]:
    validate_json_schema_instance("observation_bundle_v1.schema.json", value)
    required = {"schema_version", "bundle_id", "window", "temporal_summary", "event_refs", "entity_refs", "aggregation", "telemetry_capability_refs", "raw_evidence_refs", "feature_generation_refs", "correlation_context", "ground_truth_included", DIGEST_FIELD}
    _require_closed(value, required, required, "observation_bundle_v1")
    if value["schema_version"] != "observation_bundle_v1" or value["ground_truth_included"] is not False:
        raise ContractError("observation identity or ground-truth boundary mismatch")
    if _parse_time(value["window"]["start"]) > _parse_time(value["window"]["end"]):
        raise ContractError("observation window is reversed")
    refs = value["event_refs"]
    ids = [row["event_id"] for row in refs]
    if not ids or len(ids) != len(set(ids)) or value["aggregation"]["event_count"] != len(ids):
        raise ContractError("observation event references mismatch")
    supplied = {event["event_id"]: event for event in events}
    if supplied:
        event_times = [event["temporal"]["event_timestamp"] for event in supplied.values()]
        ingest_times = [event["temporal"]["ingest_timestamp"] for event in supplied.values()]
        if _parse_time(value["window"]["start"]) > _parse_time(min(event_times)) or _parse_time(value["window"]["end"]) < _parse_time(max(event_times)):
            raise ContractError("observation event-time window mismatch")
        if value["temporal_summary"] != {"event_time": max(event_times), "ingest_time": max(ingest_times)}:
            raise ContractError("observation temporal summary mismatch")
        for ref in refs:
            event = supplied.get(ref["event_id"])
            if event is None or ref[DIGEST_FIELD] != event[DIGEST_FIELD]:
                raise ContractError("unresolved or mismatched observation event reference")
    evidence = value["raw_evidence_refs"]
    if len({row["evidence_id"] for row in evidence}) != len(evidence):
        raise ContractError("duplicate raw evidence reference")
    if supplied and not set(value["telemetry_capability_refs"]) <= {event["event_type"] for event in supplied.values()}:
        raise ContractError("observation references unavailable telemetry capability")
    assert_no_ground_truth_leakage(value)
    verify_digest(value)
    return value


def validate_telemetry_catalog(value: dict[str, Any]) -> dict[str, Any]:
    validate_json_schema_instance("telemetry_capability_v1.schema.json", value)
    if value.get("schema_version") != "telemetry_capability_v1":
        raise ContractError("telemetry catalog identity mismatch")
    source_ids: set[str] = set()
    for source in value.get("sources", []):
        if source["source_id"] in source_ids or source["maturity"] not in MATURITY:
            raise ContractError("invalid or duplicate telemetry source")
        source_ids.add(source["source_id"])
        seen: set[str] = set()
        for capability in source["capabilities"]:
            telemetry_type = capability["telemetry_type"]
            if telemetry_type in seen or capability["maturity"] not in MATURITY:
                raise ContractError("invalid or duplicate source capability")
            if MATURITY[capability["maturity"]] > MATURITY[source["maturity"]]:
                raise ContractError("capability maturity exceeds source maturity")
            seen.add(telemetry_type)
    if not source_ids:
        raise ContractError("telemetry sources required")
    verify_digest(value)
    return value


def telemetry_vocabulary(catalog: dict[str, Any]) -> set[str]:
    return {cap["telemetry_type"] for source in catalog["sources"] for cap in source["capabilities"]}


def validate_behavior_requirements(value: dict[str, Any], taxonomy: dict[str, Any], telemetry_catalog: dict[str, Any]) -> dict[str, Any]:
    validate_json_schema_instance("behavior_telemetry_requirement_v1.schema.json", value)
    if value.get("schema_version") != "behavior_telemetry_requirement_v1" or value.get("taxonomy_id") != taxonomy.get("taxonomy_id"):
        raise ContractError("behavior telemetry mapping identity mismatch")
    taxonomy_rows = {row["node_id"]: row for row in taxonomy["nodes"]}
    vocabulary = telemetry_vocabulary(telemetry_catalog)
    seen: set[str] = set()
    for row in value.get("requirements", []):
        node_id = row["taxonomy_node_id"]
        if node_id in seen or node_id not in taxonomy_rows or not node_id.startswith("malicious."):
            raise ContractError("invalid attack taxonomy requirement reference")
        seen.add(node_id)
        required = set(row["required_all"]) | {item for group in row["required_any"] for item in group}
        useful = set(row["useful"])
        if not required or (required | useful) - vocabulary:
            raise ContractError("unknown or empty telemetry requirement")
        if required & useful:
            raise ContractError("required and useful telemetry must be disjoint")
        analogues = row["hard_benign_analogue_node_ids"]
        if not analogues or any(ref not in taxonomy_rows or not ref.startswith("benign.") for ref in analogues):
            raise ContractError("hard benign analogue reference mismatch")
    verify_digest(value)
    return value


def validate_dimension_registry(value: dict[str, Any], taxonomy: dict[str, Any]) -> dict[str, Any]:
    validate_json_schema_instance("experimental_dimension_v1.schema.json", value)
    if value.get("schema_version") != "experimental_dimension_v1":
        raise ContractError("dimension registry identity mismatch")
    dimensions = {row["dimension_id"] for row in value.get("dimensions", [])}
    if len(dimensions) != len(value.get("dimensions", [])):
        raise ContractError("duplicate experimental dimension")
    taxonomy_ids = {row["node_id"] for row in taxonomy["nodes"]}
    for design in value.get("behavior_designs", []):
        groups = [set(design[name]) for name in ("required_dimensions", "optional_dimensions", "forbidden_dimensions")]
        if design["taxonomy_node_id"] not in taxonomy_ids or any(group - dimensions for group in groups):
            raise ContractError("unknown behavior or dimension in design")
        if (groups[0] & groups[1]) or (groups[0] & groups[2]) or (groups[1] & groups[2]):
            raise ContractError("behavior dimension roles must be disjoint")
    verify_digest(value)
    return value


def validate_generator_registry(value: dict[str, Any], taxonomy: dict[str, Any], dimensions: dict[str, Any], telemetry_catalog: dict[str, Any]) -> dict[str, Any]:
    validate_json_schema_instance("generator_capability_v1.schema.json", value)
    if value.get("schema_version") != "generator_capability_v1":
        raise ContractError("generator registry identity mismatch")
    taxonomy_ids = {row["node_id"] for row in taxonomy["nodes"]}
    dimension_ids = {row["dimension_id"] for row in dimensions["dimensions"]}
    telemetry_types = telemetry_vocabulary(telemetry_catalog)
    ids: set[str] = set()
    for generator in value.get("generators", []):
        if generator["generator_id"] in ids:
            raise ContractError("duplicate generator")
        ids.add(generator["generator_id"])
        if set(generator["supported_taxonomy_nodes"]) - taxonomy_ids:
            raise ContractError("generator references unknown taxonomy node")
        if set(generator["supported_dimensions"]) - dimension_ids:
            raise ContractError("generator references unknown dimension")
        if set(generator["required_telemetry"]) - telemetry_types:
            raise ContractError("generator references unknown telemetry")
        if generator["seed_policy"] != {"deterministic": True, "algorithm": generator["seed_policy"]["algorithm"], "same_seed_same_realization": True}:
            raise ContractError("generator seed policy must be deterministic")
    verify_digest(value)
    return value


def validate_scenario_definition(value: dict[str, Any], taxonomy: dict[str, Any], generators: dict[str, Any], requirements: dict[str, Any]) -> dict[str, Any]:
    validate_json_schema_instance("scenario_definition_v2.schema.json", value)
    if value.get("schema_version") != "scenario_definition_v2":
        raise ContractError("scenario definition identity mismatch")
    taxonomy_ids = {row["node_id"] for row in taxonomy["nodes"]}
    generator_rows = {row["generator_id"]: row for row in generators["generators"]}
    node_id = value["taxonomy_node_id"]
    if node_id not in taxonomy_ids:
        raise ContractError("scenario references unknown taxonomy node")
    for generator_id in value["generator_requirements"]["allowed_generator_ids"]:
        if generator_id not in generator_rows or node_id not in generator_rows[generator_id]["supported_taxonomy_nodes"]:
            raise ContractError("generator capability mismatch")
        generator = generator_rows[generator_id]
        dimensions = set(value["intensity_model"]["dimension_ids"])
        if dimensions - set(generator["supported_dimensions"]):
            raise ContractError("scenario dimension is unsupported by generator")
        expected_events = set(value["telemetry_expectations"]["expected_event_types"])
        if expected_events - set(generator["emitted_observable_activity"]):
            raise ContractError("generator cannot emit an expected observation type")
        provided_telemetry = set(generator["required_telemetry"]) | set(generator["emitted_observable_activity"])
        if set(value["telemetry_expectations"]["required"]) - provided_telemetry:
            raise ContractError("generator does not provide required scenario telemetry")
    requirement = next((row for row in requirements["requirements"] if node_id == row["taxonomy_node_id"] or node_id.startswith(row["taxonomy_node_id"] + ".")), None)
    if requirement:
        declared = set(value["telemetry_expectations"]["required"])
        if not set(requirement["required_all"]) <= declared or any(not declared.intersection(group) for group in requirement["required_any"]):
            raise ContractError("scenario telemetry does not satisfy behavior requirement")
    if set(value["forbidden_observable_fields"]) != GROUND_TRUTH_KEYS:
        raise ContractError("scenario must forbid the complete leakage field set")
    if not value["purpose_ru"].strip() or not value["forbidden_marker_patterns"]:
        raise ContractError("scenario purpose and forbidden marker patterns are required")
    observable = " ".join(value["expected_observable_behavior"]).lower()
    if any(marker.lower() in observable for marker in value["forbidden_marker_patterns"]):
        raise ContractError("forbidden marker appears in observable description")
    verify_digest(value)
    return value


def build_scenario_realization(definition: dict[str, Any], generator_id: str, seed: int, parameters: dict[str, Any], environment_binding: dict[str, Any], ground_truth_ref: dict[str, str]) -> dict[str, Any]:
    if seed < 0:
        raise ContractError("scenario seed must be non-negative")
    base = {
        "schema_version": "scenario_realization_v1",
        "scenario_ref": {"scenario_id": definition["scenario_id"], DIGEST_FIELD: definition[DIGEST_FIELD]},
        "generator_id": generator_id,
        "seed": seed,
        "resolved_parameters": deepcopy(parameters),
        "environment_binding": deepcopy(environment_binding),
        "expected_observable_types": list(definition["telemetry_expectations"]["expected_event_types"]),
        "ground_truth_ref": deepcopy(ground_truth_ref),
    }
    return with_digest(base, id_field="realization_id", id_prefix="real")


def validate_scenario_realization(value: dict[str, Any]) -> dict[str, Any]:
    validate_json_schema_instance("scenario_realization_v1.schema.json", value)
    if value.get("schema_version") != "scenario_realization_v1" or value.get("seed", -1) < 0:
        raise ContractError("scenario realization identity mismatch")
    expected_id = with_digest({key: item for key, item in value.items() if key not in {"realization_id", DIGEST_FIELD}}, id_field="realization_id", id_prefix="real")["realization_id"]
    if value.get("realization_id") != expected_id:
        raise ContractError("scenario realization ID mismatch")
    verify_digest(value)
    return value


def validate_feature_compatibility(value: dict[str, Any], available_event_types: Iterable[str]) -> dict[str, Any]:
    validate_json_schema_instance("feature_compatibility_v1.schema.json", value)
    if value.get("schema_version") != "feature_compatibility_v1":
        raise ContractError("feature compatibility identity mismatch")
    feature = value["feature_contract"]
    names = feature["ordered_feature_names"]
    if feature["contract_id"] == "network_features_v2":
        path = ROOT / feature["contract_path"]
        if hashlib.sha256(path.read_bytes()).hexdigest() != feature["contract_sha256"]:
            raise ContractError("historical feature contract digest mismatch")
        lines = path.read_text(encoding="utf-8").splitlines()
        start = lines.index("features:") + 1
        observed = [line.strip()[2:] for line in lines[start:] if line.startswith("  - ")]
        if observed != names or feature["feature_count"] != 51 or not feature["order_immutable"]:
            raise ContractError("historical 51-feature order mismatch")
    if not set(value["input_event_types"]) <= set(available_event_types):
        raise ContractError("feature provider telemetry unavailable")
    verify_digest(value)
    return value


def load_vnext_catalogs() -> dict[str, dict[str, Any]]:
    names = {
        "taxonomy": "behavior_taxonomy_v1.json",
        "telemetry": "telemetry_capability_catalog_v1.json",
        "requirements": "behavior_telemetry_requirements_v1.json",
        "dimensions": "experimental_dimensions_v1.json",
        "generators": "generator_capabilities_v1.json",
        "legacy_features": "legacy_network_features_v2_compatibility.json",
    }
    return {key: load_json(CONTRACT_ROOT / name) for key, name in names.items()}


def audit_telemetry_scenario_foundation() -> dict[str, Any]:
    catalogs = load_vnext_catalogs()
    validate_taxonomy(catalogs["taxonomy"])
    telemetry = validate_telemetry_catalog(catalogs["telemetry"])
    requirements = validate_behavior_requirements(catalogs["requirements"], catalogs["taxonomy"], telemetry)
    dimensions = validate_dimension_registry(catalogs["dimensions"], catalogs["taxonomy"])
    generators = validate_generator_registry(catalogs["generators"], catalogs["taxonomy"], dimensions, telemetry)
    validate_feature_compatibility(catalogs["legacy_features"], EVENT_PAYLOAD_REQUIRED)
    return {
        "valid": True,
        "telemetry_source_count": len(telemetry["sources"]),
        "telemetry_type_count": len(telemetry_vocabulary(telemetry)),
        "behavior_requirement_count": len(requirements["requirements"]),
        "dimension_count": len(dimensions["dimensions"]),
        "behavior_design_count": len(dimensions["behavior_designs"]),
        "generator_count": len(generators["generators"]),
        "legacy_feature_count": catalogs["legacy_features"]["feature_contract"]["feature_count"],
        "scientific_execution_performed": False,
    }

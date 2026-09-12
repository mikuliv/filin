"""Детерминированные проверки draft-контрактов Filin vNext без runtime-связей."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
CONTRACT_ROOT = ROOT / "contracts" / "vnext"
SCHEMA_NAMES = tuple(sorted(path.name for path in CONTRACT_ROOT.glob("*.schema.json")))


class ContractError(ValueError):
    """Нарушение структурного или межполевого инварианта vNext."""


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def canonical_digest(value: Any, *, excluded_fields: tuple[str, ...] = ()) -> str:
    if isinstance(value, dict) and excluded_fields:
        value = {key: item for key, item in value.items() if key not in excluded_fields}
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ContractError(f"object required: {path}")
    return value


def validate_schema_foundation(schema: dict[str, Any]) -> None:
    if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
        raise ContractError("JSON Schema draft mismatch")
    if not str(schema.get("$id", "")).startswith("filin://vnext/"):
        raise ContractError("vNext schema ID mismatch")
    if schema.get("type") != "object" or schema.get("additionalProperties") is not False:
        raise ContractError("closed root object required")
    required = schema.get("required")
    properties = schema.get("properties")
    if not isinstance(required, list) or not required or not isinstance(properties, dict):
        raise ContractError("required fields and properties are mandatory")
    if set(required) - set(properties):
        raise ContractError("required field without property")


def _schema_type_matches(value: Any, expected: str) -> bool:
    return {
        "object": isinstance(value, dict),
        "array": isinstance(value, list),
        "string": isinstance(value, str),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "number": isinstance(value, (int, float)) and not isinstance(value, bool),
        "boolean": isinstance(value, bool),
        "null": value is None,
    }.get(expected, False)


def _resolve_local_ref(root_schema: dict[str, Any], reference: str) -> dict[str, Any]:
    if not reference.startswith("#/"):
        raise ContractError(f"external schema reference is not supported: {reference}")
    current: Any = root_schema
    for token in reference[2:].split("/"):
        token = token.replace("~1", "/").replace("~0", "~")
        if not isinstance(current, dict) or token not in current:
            raise ContractError(f"unresolved local schema reference: {reference}")
        current = current[token]
    if not isinstance(current, dict):
        raise ContractError(f"schema reference is not an object: {reference}")
    return current


def _validate_schema_node(value: Any, schema: dict[str, Any], root_schema: dict[str, Any], path: str) -> None:
    if "$ref" in schema:
        _validate_schema_node(value, _resolve_local_ref(root_schema, schema["$ref"]), root_schema, path)
        return
    if "oneOf" in schema:
        matches = 0
        for option in schema["oneOf"]:
            try:
                _validate_schema_node(value, option, root_schema, path)
                matches += 1
            except ContractError:
                pass
        if matches != 1:
            raise ContractError(f"{path}: expected exactly one schema match, got {matches}")
        return
    if "const" in schema and value != schema["const"]:
        raise ContractError(f"{path}: constant mismatch")
    if "enum" in schema and value not in schema["enum"]:
        raise ContractError(f"{path}: value is not in enum")
    expected = schema.get("type")
    if expected is not None:
        expected_types = [expected] if isinstance(expected, str) else expected
        if not any(_schema_type_matches(value, item) for item in expected_types):
            raise ContractError(f"{path}: type mismatch")
    if isinstance(value, dict):
        required = set(schema.get("required", []))
        missing = required - set(value)
        if missing:
            raise ContractError(f"{path}: missing fields: {sorted(missing)}")
        properties = schema.get("properties", {})
        additional = schema.get("additionalProperties", True)
        for key, item in value.items():
            if key in properties:
                _validate_schema_node(item, properties[key], root_schema, f"{path}.{key}")
            elif additional is False:
                raise ContractError(f"{path}: unexpected field: {key}")
            elif isinstance(additional, dict):
                _validate_schema_node(item, additional, root_schema, f"{path}.{key}")
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0) or len(value) > schema.get("maxItems", len(value)):
            raise ContractError(f"{path}: array length mismatch")
        if schema.get("uniqueItems") and len({canonical_bytes(item) for item in value}) != len(value):
            raise ContractError(f"{path}: duplicate array item")
        if isinstance(schema.get("items"), dict):
            for index, item in enumerate(value):
                _validate_schema_node(item, schema["items"], root_schema, f"{path}[{index}]")
    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0) or len(value) > schema.get("maxLength", len(value)):
            raise ContractError(f"{path}: string length mismatch")
        if "pattern" in schema and re.search(schema["pattern"], value) is None:
            raise ContractError(f"{path}: pattern mismatch")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            raise ContractError(f"{path}: below minimum")
        if "maximum" in schema and value > schema["maximum"]:
            raise ContractError(f"{path}: above maximum")


def validate_json_schema_instance(schema_name: str, value: Any) -> None:
    """Проверяет документ поддерживаемым подмножеством JSON Schema 2020-12.

    Подмножество намеренно не заменяет внешний стандартный валидатор: оно даёт
    автономную fail-closed проверку используемых в vNext ключевых слов.
    """
    if schema_name not in SCHEMA_NAMES:
        raise ContractError(f"unknown vNext schema: {schema_name}")
    schema = load_json(CONTRACT_ROOT / schema_name)
    validate_schema_foundation(schema)
    _validate_schema_node(value, schema, schema, "$")


def validate_taxonomy(value: dict[str, Any]) -> dict[str, Any]:
    if value.get("schema_version") != "behavior_taxonomy_v1" or value.get("status") not in {"draft", "reviewed", "frozen"}:
        raise ContractError("taxonomy identity mismatch")
    nodes = value.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        raise ContractError("taxonomy nodes required")
    by_id = {row.get("node_id"): row for row in nodes if isinstance(row, dict)}
    if len(by_id) != len(nodes) or None in by_id:
        raise ContractError("taxonomy node IDs must be unique")
    roots = {"benign", "malicious"}
    if {node_id for node_id, row in by_id.items() if row.get("parent_id") is None} != roots:
        raise ContractError("exact benign and malicious roots required")
    level_order = {"superclass": 0, "behavioral_family": 1, "behavior": 2, "scenario_variant": 3}
    for node_id, row in by_id.items():
        parent_id = row.get("parent_id")
        if parent_id is None:
            if row.get("level") != "superclass":
                raise ContractError("root level mismatch")
            continue
        if parent_id not in by_id or not node_id.startswith(parent_id + "."):
            raise ContractError("taxonomy parent mismatch")
        if level_order.get(row.get("level"), -1) != level_order.get(by_id[parent_id].get("level"), -2) + 1:
            raise ContractError("taxonomy level transition mismatch")
        seen = {node_id}
        cursor = parent_id
        while cursor is not None:
            if cursor in seen:
                raise ContractError("taxonomy cycle")
            seen.add(cursor)
            cursor = by_id[cursor].get("parent_id")
    if any(row.get("capability_status") != "planned" for row in nodes):
        raise ContractError("draft taxonomy must not overstate capability")
    if "unknown" in by_id:
        raise ContractError("unknown is a detection state, not taxonomy ground truth")
    return value


def validate_recovery_manifest(value: dict[str, Any]) -> dict[str, Any]:
    if value.get("schema_version") != "execution_recovery_manifest_v1":
        raise ContractError("recovery manifest identity mismatch")
    policy = value.get("restore_policy", {})
    expected = {"network_pull": "forbidden", "floating_base_images": "forbidden", "automatic_rebuild": "forbidden", "automatic_lock_rewrite": "forbidden", "identity_mismatch": "fail_closed"}
    if policy != expected:
        raise ContractError("recovery must be offline and fail closed")
    images = value.get("images")
    if not isinstance(images, list) or not images:
        raise ContractError("offline image inventory required")
    names = [row.get("logical_name") for row in images]
    archives = [row.get("archive_path") for row in images]
    if len(set(names)) != len(names) or len(set(archives)) != len(archives):
        raise ContractError("recovery image identity must be unique")
    if any(not str(path).startswith("images/") or ".." in Path(str(path)).parts for path in archives):
        raise ContractError("unsafe recovery archive path")
    return value


def audit_foundation() -> dict[str, Any]:
    schemas = []
    for name in SCHEMA_NAMES:
        value = load_json(CONTRACT_ROOT / name)
        validate_schema_foundation(value)
        schemas.append({"path": name, "schema_id": value["$id"], "sha256": canonical_digest(value)})
    taxonomy = validate_taxonomy(load_json(CONTRACT_ROOT / "behavior_taxonomy_v1.json"))
    return {
        "valid": True,
        "schema_count": len(schemas),
        "schemas": schemas,
        "taxonomy_node_count": len(taxonomy["nodes"]),
        "taxonomy_digest": canonical_digest(taxonomy),
        "scientific_execution_performed": False,
        "historical_artifacts_modified": False,
    }

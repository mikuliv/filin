from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

SCENARIO_SCHEMA = "network_validation_scenario_v1"
CAMPAIGN_SCHEMA = "network_validation_campaign_v1"
EXECUTION_SCHEMA = "network_validation_execution_event_v1"
MARKER_SCHEMA = "network_validation_marker_event_v1"
CAPTURE_SCHEMA = "network_validation_capture_manifest_v1"
PARAMETER_SCHEMA = "network_validation_parameter_realization_v1"
LABEL_SCHEMA = "network_validation_sealed_label_mapping_v1"
ENVIRONMENT_SCHEMA = "network_validation_environment_lock_v1"
FREEZE_SCHEMA = "network_validation_freeze_preview_v1"

TOKEN = re.compile(r"^[a-z][a-z0-9_-]{2,63}$")
BEHAVIORS = {
    "navigation",
    "credential_rejection",
    "periodic_callback",
    "throttled_pressure",
    "service_discovery",
    "path_inspection",
}
FAMILIES = {"family_a", "family_b"}
FORBIDDEN_MODEL_FIELDS = {
    "label", "class", "class_name", "true_class", "scenario_id", "scenario_token",
    "campaign_id", "campaign_token", "generator_family", "infrastructure_id",
    "infrastructure_profile", "target_implementation", "filename", "file_path",
    "directory", "directory_name", "marker_nonce", "pair_id",
}


class ContractError(ValueError):
    pass


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _exact(value: dict[str, Any], required: set[str], optional: set[str] = set()) -> None:
    missing = required - value.keys()
    unknown = value.keys() - required - optional
    if missing:
        raise ContractError(f"missing fields: {sorted(missing)}")
    if unknown:
        raise ContractError(f"unknown fields: {sorted(unknown)}")


def _token(value: Any, field: str) -> str:
    text = str(value)
    if not TOKEN.fullmatch(text):
        raise ContractError(f"invalid {field}")
    return text


def _integer(value: Any, field: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise ContractError(f"invalid {field}")
    return value


def _timestamp(value: Any, field: str) -> datetime:
    if not isinstance(value, str):
        raise ContractError(f"invalid {field}")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ContractError(f"invalid {field}") from error


def _validate_parameter_vector(value: dict[str, Any], family: str, behavior: str, request_count: int) -> None:
    fields = {
        ("family_a", "navigation"): {"path_rotation"},
        ("family_b", "navigation"): {"phase_rotation"},
        ("family_a", "credential_rejection"): {"credential_rotation"},
        ("family_b", "credential_rejection"): {"session_rotation"},
        ("family_a", "periodic_callback"): {"cadence_mode"},
        ("family_b", "periodic_callback"): {"cadence_mode"},
        ("family_a", "throttled_pressure"): {"burst_width"},
        ("family_b", "throttled_pressure"): {"phase_width"},
        ("family_a", "service_discovery"): {"ports"},
        ("family_b", "service_discovery"): {"port_start", "port_width"},
        ("family_a", "path_inspection"): {"path_set"},
        ("family_b", "path_inspection"): {"path_set"},
    }[(family, behavior)]
    _exact(value, fields)
    if set(value) & FORBIDDEN_MODEL_FIELDS:
        raise ContractError("labels and provenance are forbidden in parameter vectors")
    for name in fields & {"path_rotation", "phase_rotation"}:
        _integer(value[name], name, 0, 1000)
    for name in fields & {"credential_rotation", "session_rotation", "burst_width", "phase_width"}:
        _integer(value[name], name, 1, 1000)
    if "cadence_mode" in fields and value["cadence_mode"] not in {"steady", "jittered", "phased"}:
        raise ContractError("invalid cadence mode")
    if "path_set" in fields and not isinstance(value["path_set"], str):
        raise ContractError("invalid path set")
    if "ports" in fields:
        ports = value["ports"]
        if not isinstance(ports, list) or len(ports) < request_count:
            raise ContractError("insufficient service-discovery ports")
        for port in ports:
            _integer(port, "port", 1, 65535)
    if "port_start" in fields:
        start = _integer(value["port_start"], "port_start", 1, 65535)
        width = _integer(value["port_width"], "port_width", request_count, 1000)
        if start + width - 1 > 65535:
            raise ContractError("service-discovery port range exceeds 65535")


def validate_scenario(value: dict[str, Any]) -> dict[str, Any]:
    required = {
        "schema_version", "scenario_token", "behavior_type", "generator_family", "parameter_vector",
        "target_capability", "requested_duration_seconds", "requested_request_count",
        "requested_spacing_ms", "requested_payload_size", "retry_policy", "timeout_policy",
        "response_order_expectation", "background_traffic_policy", "seed", "campaign_token",
        "infrastructure_profile", "capture_policy",
    }
    _exact(value, required)
    if value["schema_version"] != SCENARIO_SCHEMA:
        raise ContractError("unsupported scenario schema")
    _token(value["scenario_token"], "scenario_token")
    _token(value["campaign_token"], "campaign_token")
    _token(value["infrastructure_profile"], "infrastructure_profile")
    if value["behavior_type"] not in BEHAVIORS:
        raise ContractError("unsupported behavior_type")
    if value["generator_family"] not in FAMILIES:
        raise ContractError("unsupported generator_family")
    if value["target_capability"] not in {"web", "api", "control", "multi_port"}:
        raise ContractError("unsupported target_capability")
    _integer(value["requested_duration_seconds"], "requested_duration_seconds", 1, 3600)
    _integer(value["requested_request_count"], "requested_request_count", 1, 10000)
    _integer(value["requested_spacing_ms"], "requested_spacing_ms", 1, 60000)
    _integer(value["requested_payload_size"], "requested_payload_size", 0, 1048576)
    _integer(value["seed"], "seed", 0, 2147483647)
    if not isinstance(value["parameter_vector"], dict) or not value["parameter_vector"]:
        raise ContractError("parameter_vector must be a non-empty object")
    _validate_parameter_vector(value["parameter_vector"], value["generator_family"], value["behavior_type"], value["requested_request_count"])
    _exact(value["retry_policy"], {"max_retries", "backoff_ms"})
    _integer(value["retry_policy"]["max_retries"], "max_retries", 0, 10)
    _integer(value["retry_policy"]["backoff_ms"], "backoff_ms", 0, 60000)
    _exact(value["timeout_policy"], {"connect_ms", "read_ms", "expected"})
    _integer(value["timeout_policy"]["connect_ms"], "connect_ms", 1, 120000)
    _integer(value["timeout_policy"]["read_ms"], "read_ms", 1, 120000)
    if value["timeout_policy"]["expected"] not in {"response", "timeout", "either"}:
        raise ContractError("invalid timeout expectation")
    if value["response_order_expectation"] not in {"normal", "reverse", "delayed"}:
        raise ContractError("invalid response order")
    _exact(value["background_traffic_policy"], {"http_requests", "dns_queries", "keepalive_count"})
    for field in ("http_requests", "dns_queries", "keepalive_count"):
        _integer(value["background_traffic_policy"][field], field, 0, 1000)
    _exact(value["capture_policy"], {"interface", "bpf", "marker_copies"})
    if value["capture_policy"]["interface"] != "any":
        raise ContractError("capture interface must cover all client networks")
    _integer(value["capture_policy"]["marker_copies"], "marker_copies", 1, 5)
    if value["capture_policy"]["bpf"] != "tcp or udp port 53":
        raise ContractError("unsupported capture filter")
    if any(field in value for field in FORBIDDEN_MODEL_FIELDS & {"label", "class", "true_class"}):
        raise ContractError("labels are forbidden in execution scenarios")
    canonical_bytes(value)
    return value


def validate_campaign(value: dict[str, Any]) -> dict[str, Any]:
    required = {
        "schema_version", "campaign_token", "technical_fixture", "scenarios", "infrastructure_profiles",
        "counterfactual_pairs", "counterfactual_requirements", "split_policy", "baseline_plan", "acceptance_criteria",
        "feature_contract_path", "candidate_identity",
    }
    _exact(value, required)
    if value["schema_version"] != CAMPAIGN_SCHEMA:
        raise ContractError("unsupported campaign schema")
    _token(value["campaign_token"], "campaign_token")
    if value["technical_fixture"] is not True:
        raise ContractError("only disposable technical fixtures are accepted before freeze")
    scenarios = value["scenarios"]
    if not isinstance(scenarios, list) or not scenarios:
        raise ContractError("campaign scenarios are required")
    tokens = []
    for scenario in scenarios:
        validate_scenario(scenario)
        if scenario["campaign_token"] != value["campaign_token"]:
            raise ContractError("scenario campaign token mismatch")
        tokens.append(scenario["scenario_token"])
    if len(tokens) != len(set(tokens)):
        raise ContractError("duplicate scenario token")
    required_counterfactuals = {
        "same_class_different_ports", "same_class_different_http_paths",
        "same_class_different_response_statuses", "same_class_different_timing",
        "different_classes_same_intensity", "different_classes_same_ports",
        "benign_attack_like_intensity", "attack_benign_like_intensity",
        "same_behavior_different_targets",
    }
    if set(value["counterfactual_requirements"]) != required_counterfactuals:
        raise ContractError("counterfactual requirement plan is incomplete")
    baseline_fields = {"name", "allowed_features", "forbidden_metadata", "training_split", "evaluation_split", "fixed_hyperparameters", "metric_set"}
    required_baselines = {"majority", "ports_services_only", "traffic_rate_only", "http_only", "timing_only", "rolling_only", "infrastructure_only", "generator_family_only", "shallow_decision_tree", "logistic_regression", "intended_candidate"}
    names = set()
    for baseline in value["baseline_plan"]:
        _exact(baseline, baseline_fields)
        names.add(baseline["name"])
    if names != required_baselines:
        raise ContractError("baseline plan is incomplete")
    acceptance_fields = {
        "minimum_candidate_macro_f1", "maximum_false_positive_rate", "minimum_per_class_recall",
        "maximum_unseen_generator_performance_drop", "minimum_margin_over_infrastructure_only",
        "minimum_margin_over_ports_services_only", "parameter_realization_pass_rate",
        "required_counterfactual_pass_rate", "required_external_corpus_result", "permitted_exclusions",
        "maximum_excluded_row_share",
    }
    _exact(value["acceptance_criteria"], acceptance_fields)
    _exact(value["candidate_identity"], {"mode", "candidate_id", "training_allowed"})
    if value["candidate_identity"]["mode"] != "existing_candidate_integrity_only":
        raise ContractError("unsupported candidate identity mode")
    if not re.fullmatch(r"v[0-9]+:[a-f0-9]{16}", str(value["candidate_identity"]["candidate_id"])):
        raise ContractError("invalid candidate identity")
    if value["candidate_identity"]["training_allowed"] is not False:
        raise ContractError("training must remain disabled")
    return value


def validate_model_input(row: dict[str, Any], feature_order: list[str]) -> None:
    forbidden = sorted(set(row) & FORBIDDEN_MODEL_FIELDS)
    if forbidden:
        raise ContractError(f"forbidden model metadata: {forbidden}")
    if list(row) != feature_order:
        raise ContractError("model feature order mismatch")
    if any(not isinstance(value, (int, float)) or isinstance(value, bool) for value in row.values()):
        raise ContractError("model features must be numeric")


def validate_sealed_label_mapping(value: dict[str, Any]) -> None:
    _exact(value, {"schema_version", "scenario_token", "evaluation_label"})
    if value["schema_version"] != LABEL_SCHEMA:
        raise ContractError("label mapping schema mismatch")
    _token(value["scenario_token"], "scenario_token")
    if value["evaluation_label"] not in {
        "benign", "auth_failures", "beacon", "low_rate_dos", "port_scan", "web_probe"
    }:
        raise ContractError("unsupported evaluation label")
    canonical_bytes(value)


def validate_event(value: dict[str, Any], kind: str) -> None:
    common = {"schema_version", "campaign_token", "scenario_token"}
    if kind == "execution":
        required = common | {
            "generator_family", "infrastructure_profile", "client_identity", "target_identity",
            "start_timestamp", "end_timestamp", "exit_code", "execution_status",
            "requested_parameter_digest", "client_image_digest", "target_image_digest", "network_identity",
        }
        schema = EXECUTION_SCHEMA
    elif kind == "marker":
        required = common | {
            "marker_nonce", "marker_type", "monotonic_timestamp", "wall_clock_timestamp", "source", "capture_association",
        }
        schema = MARKER_SCHEMA
    else:
        raise ContractError("unknown event kind")
    _exact(value, required)
    if value["schema_version"] != schema:
        raise ContractError("event schema mismatch")
    _token(value["campaign_token"], "campaign_token")
    _token(value["scenario_token"], "scenario_token")
    if kind == "execution":
        for field in ("generator_family", "infrastructure_profile", "client_identity", "target_identity", "network_identity"):
            _token(value[field], field)
        if isinstance(value["exit_code"], bool) or not isinstance(value["exit_code"], int):
            raise ContractError("invalid exit code")
        if value["execution_status"] not in {"technical_fixture_completed", "technical_fixture_failed"}:
            raise ContractError("invalid execution status")
        start = _timestamp(value["start_timestamp"], "start_timestamp")
        end = _timestamp(value["end_timestamp"], "end_timestamp")
        if end < start:
            raise ContractError("execution interval is reversed")
        if not re.fullmatch(r"[a-f0-9]{64}", str(value["requested_parameter_digest"])):
            raise ContractError("invalid parameter digest")
        for field in ("client_image_digest", "target_image_digest"):
            if value[field] != "unresolved" and not re.fullmatch(r"sha256:[a-f0-9]{64}", str(value[field])):
                raise ContractError(f"invalid {field}")
    else:
        if value["marker_type"] not in {"start", "end"}:
            raise ContractError("invalid marker type")
        if not re.fullmatch(r"[a-f0-9]{24,64}", str(value["marker_nonce"])):
            raise ContractError("invalid marker nonce")
        if isinstance(value["monotonic_timestamp"], bool) or not isinstance(value["monotonic_timestamp"], (int, float)):
            raise ContractError("invalid monotonic timestamp")
        _timestamp(value["wall_clock_timestamp"], "wall_clock_timestamp")
        _token(value["source"], "source")
        _token(value["capture_association"], "capture_association")


def validate_capture_manifest(value: dict[str, Any], dataset_root: Path, execution: dict[str, Any]) -> None:
    required = {
        "schema_version", "capture_id", "campaign_token", "scenario_token", "session_token",
        "generator_family", "infrastructure_profile", "sensor_identity", "docker_network_identity",
        "capture_start", "capture_end", "source_container", "target_container", "packet_count", "byte_count",
        "pcap_path", "pcap_sha256", "zeek_status", "execution_status", "marker_association",
        "parameter_verification_status",
    }
    _exact(value, required)
    if value["schema_version"] != CAPTURE_SCHEMA:
        raise ContractError("capture schema mismatch")
    for field in ("capture_id", "campaign_token", "scenario_token", "session_token", "generator_family", "infrastructure_profile"):
        _token(value[field], field)
    path = Path(value["pcap_path"])
    if path.is_absolute() or ".." in path.parts:
        raise ContractError("pcap_path must be dataset-relative")
    actual = dataset_root / path
    if not actual.is_file():
        raise ContractError("pcap file missing")
    if hashlib.sha256(actual.read_bytes()).hexdigest() != value["pcap_sha256"]:
        raise ContractError("pcap SHA mismatch")
    if value["packet_count"] <= 0 or value["byte_count"] <= 24:
        raise ContractError("empty capture")
    if not value["capture_start"] < value["capture_end"]:
        raise ContractError("invalid capture interval")
    if value["scenario_token"] != execution["scenario_token"] or value["campaign_token"] != execution["campaign_token"]:
        raise ContractError("capture/execution mismatch")
    linked_fields = {
        "generator_family": "generator_family",
        "infrastructure_profile": "infrastructure_profile",
        "docker_network_identity": "network_identity",
        "target_container": "target_identity",
        "execution_status": "execution_status",
    }
    if any(value[manifest_field] != execution[execution_field] for manifest_field, execution_field in linked_fields.items()):
        raise ContractError("capture/execution metadata mismatch")
    if value["zeek_status"] not in {"completed", "failed"}:
        raise ContractError("invalid Zeek status")
    if value["parameter_verification_status"] not in {"passed", "failed", "incomplete"}:
        raise ContractError("invalid parameter verification status")
    if not re.fullmatch(r"[a-f0-9]{24,64}", str(value["marker_association"])):
        raise ContractError("invalid marker association")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_canonical(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(value) + b"\n")

"""Жизненный цикл и проверяемый pipeline одноразовой Docker-лаборатории vNext."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import time
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lab.network_validation.feature_adapter import SessionFeatureAdapter
from lab.sensor.zeek_log_parser import parse_zeek_log
from tools.vnext.contracts import canonical_digest
from tools.vnext.detection import detect
from tools.vnext.features import build_feature_bundle
from tools.vnext.scenarios.registry import validate_wave1_registry
from tools.vnext.context import build_context_fact, build_context_profile
from tools.vnext.graph import attach_reasoning_nodes, build_interaction_graph
from tools.vnext.correlation import build_attack_chain, build_incident_candidate, correlate, map_attack_evidence
from tools.vnext.telemetry import validate_normalized_event, validate_observation_bundle, with_digest


ROOT = Path(__file__).resolve().parents[2]
LAB = ROOT / "lab" / "vnext"
COMPOSE = LAB / "compose.vnext-lab.yml"
ARTIFACT_ROOT = ROOT / ".filin-engineering" / "vnext" / "docker-runs"
NETWORK = "filin-vnext-lab"
CONTAINERS = {
    "target-http": "filin-vnext-target-http",
    "target-auth": "filin-vnext-target-auth",
    "generator": "filin-vnext-generator",
    "sensor": "filin-vnext-sensor",
    "zeek": "filin-vnext-zeek",
}
IMAGES = {
    "target": "filin-vnext-dev/target:latest",
    "generator": "filin-vnext-dev/generator:latest",
    "sensor": "filin-vnext-dev/sensor:latest",
    "zeek": "filin-vnext-dev/zeek:latest",
}
MATRIX = (
    ("normal-navigation", "scenario_normal_navigation", "wave1_benign_operations"),
    ("health-check", "scenario_health_checks", "wave1_benign_operations"),
    ("api-polling", "scenario_api_polling", "wave1_benign_operations"),
    ("auth-misconfiguration", "scenario_auth_misconfiguration", "wave1_benign_operations"),
    ("recon-a-sequential", "scenario_sequential_port_scan", "wave1_recon_family_a"),
    ("recon-b-randomized", "scenario_randomized_port_scan", "wave1_recon_family_b"),
    ("path-enumeration", "scenario_web_path_enumeration", "wave1_web_enumerator"),
    ("credential-a-brute", "scenario_credential_brute_force", "wave1_credential_family_a"),
    ("credential-b-spray", "scenario_password_spraying", "wave1_credential_family_b"),
    ("beacon-a-periodic", "scenario_periodic_beacon", "wave1_beacon_family_a"),
    ("beacon-b-jittered", "scenario_jittered_beacon", "wave1_beacon_family_b"),
)
SEQUENCES = (
    ("repeated-discovery", (("scenario_service_discovery", "wave1_recon_family_a"), ("scenario_service_discovery", "wave1_recon_family_a")), None),
    ("approved-scanner-recurrence", (("scenario_approved_scanner", "wave1_benign_operations"), ("scenario_approved_scanner", "wave1_benign_operations")), "approved_scanner"),
    ("beacon-persistence", (("scenario_periodic_beacon", "wave1_beacon_family_a"), ("scenario_periodic_beacon", "wave1_beacon_family_a")), None),
    ("health-check-recurrence", (("scenario_health_checks", "wave1_benign_operations"), ("scenario_health_checks", "wave1_benign_operations")), "monitoring"),
    ("auth-then-service", (("scenario_credential_brute_force", "wave1_credential_family_a"), ("scenario_normal_navigation", "wave1_benign_operations")), None),
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def context_digest() -> str:
    digest = hashlib.sha256()
    roots = (ROOT / "tools" / "vnext", ROOT / "contracts" / "vnext", LAB)
    for path in sorted(p for base in roots for p in base.rglob("*") if p.is_file() and "__pycache__" not in p.parts):
        digest.update(path.relative_to(ROOT).as_posix().encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def environment() -> dict[str, str]:
    env = os.environ.copy()
    env["FILIN_VNEXT_ARTIFACT_ROOT"] = str(ARTIFACT_ROOT.resolve())
    env["FILIN_SOURCE_COMMIT"] = command(["git", "rev-parse", "HEAD"], capture=True).strip()
    env["FILIN_BUILD_TIMESTAMP"] = utc_now()
    env["FILIN_BUILD_CONTEXT_SHA256"] = context_digest()
    for name in ("target", "generator", "sensor", "zeek"):
        env[f"FILIN_{name.upper()}_DOCKERFILE_SHA256"] = sha256(LAB / f"Dockerfile.{name}")
    return env


def command(args: list[str], *, capture: bool = False, check: bool = True, env: dict[str, str] | None = None) -> str:
    result = subprocess.run(args, cwd=ROOT, env=env, text=True, encoding="utf-8", errors="replace", capture_output=capture, check=False)
    if check and result.returncode:
        raise RuntimeError(f"command failed ({result.returncode}): {' '.join(args)}\n{result.stdout}\n{result.stderr}")
    return (result.stdout + result.stderr) if capture else ""


def compose(*args: str, capture: bool = False, check: bool = True) -> str:
    return command(["docker", "compose", "-f", str(COMPOSE), *args], capture=capture, check=check, env=environment())


def docker_available() -> tuple[bool, str]:
    try:
        value = command(["docker", "info", "--format", "{{.ServerVersion}}"], capture=True).strip()
        return bool(value), value or "Docker daemon did not report a version"
    except (OSError, RuntimeError) as exc:
        return False, str(exc)


def up() -> None:
    ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)
    (ARTIFACT_ROOT / "target").mkdir(exist_ok=True)
    compose("build")
    compose("up", "-d", "target-http", "target-auth", "generator", "sensor", "zeek")
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        probe = command(["docker", "exec", CONTAINERS["generator"], "python", "-c", "import http.client; c=http.client.HTTPConnection('target-http',8080,timeout=.5); c.request('GET','/status'); r=c.getresponse(); r.read(); assert r.status==200"], capture=True, check=False)
        if not probe:
            return
        time.sleep(0.4)
    raise RuntimeError("laboratory targets did not become ready")


def _container_ip(name: str) -> str:
    return command(["docker", "inspect", "-f", f"{{{{(index .NetworkSettings.Networks \"{NETWORK}\").IPAddress}}}}", name], capture=True).strip()


def _image_ids() -> dict[str, str]:
    return {name: command(["docker", "image", "inspect", "--format", "{{.Id}}", image], capture=True).strip() for name, image in IMAGES.items()}


def _raw_ref(path: Path, locator: str, artifact_type: str = "log") -> dict[str, Any]:
    digest = sha256(path)
    return {"evidence_id": "raw_" + digest, "artifact_type": artifact_type, "sha256": digest, "size_bytes": path.stat().st_size, "locator": locator}


def _entity_id(kind: str, value: str) -> str:
    return "ent_" + canonical_digest({"kind": kind, "value": value})


def _iso(ts: Any) -> str:
    if isinstance(ts, (int, float)) or str(ts).replace(".", "", 1).isdigit():
        return datetime.fromtimestamp(float(ts), timezone.utc).isoformat().replace("+00:00", "Z")
    return str(ts)


def _event(event_type: str, row: dict[str, Any], raw: dict[str, Any], sequence: int, payload: dict[str, Any], source_ip: str, destination_ip: str, action: str, outcome: str, status: str) -> dict[str, Any]:
    parsed = canonical_digest(row)
    refs = [
        {"role": "source", "entity_id": _entity_id("ip", source_ip), "entity_type": "ip"},
        {"role": "destination", "entity_id": _entity_id("ip", destination_ip), "entity_type": "ip"},
    ]
    if event_type == "auth.attempt":
        refs.append({"role": "target", "entity_id": payload["target_service_entity_id"], "entity_type": "service"})
    base = {
        "schema_version": "normalized_security_event_v1", "event_type": event_type, "stage": "normalized",
        "source": {"source_type": "docker_lab_telemetry", "source_product": "zeek" if event_type != "auth.attempt" else "filin_target_auth", "source_component": raw["locator"].split("/")[-1], "collector": "vnext_docker_normalizer", "collector_version": "1.0.0"},
        "temporal": {"event_timestamp": _iso(row["ts"] if "ts" in row else row["timestamp"]), "ingest_timestamp": utc_now(), "ordering": {"domain": NETWORK, "sequence": sequence}},
        "entity_refs": refs, "action": {"name": action, "outcome": outcome, "status": status}, "payload": payload,
        "provenance": {"source_record_id": f"{raw['evidence_id']}:{sequence}", "raw_evidence": {**raw, "record_offset": sequence}, "transformation_chain": [
            {"stage": "parsed", "component": "lab.sensor.zeek_log_parser", "version": "existing", "input_digest": raw["sha256"], "output_digest": parsed},
            {"stage": "normalized", "component": "vnext_docker_normalizer", "version": "1.0.0", "input_digest": parsed, "output_digest": canonical_digest(payload)},
        ]}, "enrichments": [],
    }
    value = with_digest(base, id_field="event_id", id_prefix="evt")
    return validate_normalized_event(value)


def normalize(case_dir: Path, generator_ip: str, target_ip: str, auth_case: bool) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    zeek_dir = case_dir / "zeek"
    rel = case_dir.relative_to(ARTIFACT_ROOT).as_posix()
    pcap = _raw_ref(case_dir / "capture" / "traffic.pcap", f"{rel}/capture/traffic.pcap", "pcap")
    conn_path = zeek_dir / "conn.log"
    conn_raw = _raw_ref(conn_path, f"{rel}/zeek/conn.log")
    conn_rows = [row for row in parse_zeek_log(conn_path) if row.get("id.orig_h") == generator_ip and row.get("id.resp_h") == target_ip]
    if not conn_rows:
        raise AssertionError("conn.log has no generator-to-target connection")
    events: list[dict[str, Any]] = []
    for row in conn_rows:
        orig_bytes, resp_bytes = int(row.get("orig_bytes") or 0), int(row.get("resp_bytes") or 0)
        orig_pkts, resp_pkts = int(row.get("orig_pkts") or 0), int(row.get("resp_pkts") or 0)
        payload = {"namespace": "network.flow", "source": {"ip": generator_ip, "port": int(row["id.orig_p"])}, "destination": {"ip": target_ip, "port": int(row["id.resp_p"])}, "transport": row.get("proto", "tcp"), "application_protocol": row.get("service") or "unknown", "direction": "internal", "bytes": orig_bytes + resp_bytes, "packets": orig_pkts + resp_pkts, "connection_state": row.get("conn_state", "unknown")}
        events.append(_event("network.flow", row, conn_raw, len(events), payload, generator_ip, target_ip, "connect", "success" if row.get("conn_state") not in {"S0", "REJ"} else "failure", row.get("conn_state", "unknown")))
    raw_refs = [pcap, conn_raw]
    http_path = zeek_dir / "http.log"
    if http_path.is_file() and http_path.stat().st_size:
        http_raw = _raw_ref(http_path, f"{rel}/zeek/http.log")
        raw_refs.append(http_raw)
        for row in parse_zeek_log(http_path):
            if row.get("id.orig_h") != generator_ip or row.get("id.resp_h") != target_ip:
                continue
            code = int(row.get("status_code") or 0)
            if not 100 <= code <= 599:
                continue
            payload = {"namespace": "http.request", "method": row.get("method") or "UNKNOWN", "scheme": "http", "host": row.get("host") or target_ip, "path": row.get("uri") or "/", "status_code": code, "request_bytes": int(row.get("request_body_len") or 0), "response_bytes": int(row.get("response_body_len") or 0)}
            events.append(_event("http.request", row, http_raw, len(events), payload, generator_ip, target_ip, "request", "success" if code < 400 else "failure", str(code)))
    auth_path = case_dir / "raw" / "auth.jsonl"
    if auth_case:
        auth_raw = _raw_ref(auth_path, f"{rel}/raw/auth.jsonl", "jsonl")
        raw_refs.append(auth_raw)
        for row in parse_zeek_log(auth_path):
            account = str(row.get("account", "unknown"))
            success = bool(row.get("success"))
            service = _entity_id("service", "vnext-docker-auth")
            payload = {"namespace": "auth.attempt", "account_entity_id": _entity_id("account", account), "authentication_type": "password", "success": success, "failure_reason": str(row.get("failure_reason", "none")), "target_service_entity_id": service}
            events.append(_event("auth.attempt", row, auth_raw, len(events), payload, str(row.get("remote_ip") or generator_ip), target_ip, "authenticate", "success" if success else "failure", str(row.get("status_code", "unknown"))))
    times = [row["temporal"]["event_timestamp"] for row in events]
    ingest_times = [row["temporal"]["ingest_timestamp"] for row in events]
    observation_base = {
        "schema_version": "observation_bundle_v1", "window": {"start": min(times), "end": max(times), "ordering_domain": NETWORK},
        "temporal_summary": {"event_time": max(times), "ingest_time": max(ingest_times)},
        "event_refs": [{"event_id": row["event_id"], "canonical_digest": row["canonical_digest"]} for row in events], "entity_refs": [],
        "aggregation": {"method": "docker_execution_window", "builder": "vnext_docker_observation_builder", "builder_version": "1.0.0", "causal": True, "event_count": len(events)},
        "telemetry_capability_refs": sorted({row["event_type"] for row in events}), "raw_evidence_refs": [{"evidence_id": row["evidence_id"], "sha256": row["sha256"]} for row in raw_refs], "feature_generation_refs": [],
        "correlation_context": {"correlation_keys": ["source.ip", "destination.ip"], "parent_bundle_refs": []}, "ground_truth_included": False,
    }
    observation = with_digest(observation_base, id_field="bundle_id", id_prefix="obs")
    validate_observation_bundle(observation, events=events)
    return events, observation, {"pcap": pcap, "logs": raw_refs[1:]}


def _write(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def run_case(campaign: str, slug: str, scenario: str, generator: str, seed: int) -> dict[str, Any]:
    case_dir = ARTIFACT_ROOT / "runs" / campaign / slug
    case_locator = case_dir.relative_to(ARTIFACT_ROOT).as_posix()
    (case_dir / "capture").mkdir(parents=True, exist_ok=False)
    (case_dir / "zeek").mkdir()
    (case_dir / "raw").mkdir()
    auth_case = scenario in {"scenario_auth_misconfiguration", "scenario_credential_brute_force", "scenario_password_spraying"}
    target_name = CONTAINERS["target-auth" if auth_case else "target-http"]
    generator_ip, target_ip = _container_ip(CONTAINERS["generator"]), _container_ip(target_name)
    current_pcap = ARTIFACT_ROOT / "current.pcap"
    current_result = ARTIFACT_ROOT / "generator-result.json"
    auth_current = ARTIFACT_ROOT / "target" / "auth.jsonl"
    for path in (current_pcap, current_result, auth_current):
        path.unlink(missing_ok=True)
    command(["docker", "exec", "-d", CONTAINERS["sensor"], "tcpdump", "-i", "eth0", "-U", "-s", "0", "-w", "/artifacts/current.pcap", "tcp"])
    time.sleep(0.35)
    command(["docker", "exec", CONTAINERS["generator"], "python", "-m", "lab.vnext.generator_runner", "--scenario", scenario, "--generator", generator, "--seed", str(seed)])
    time.sleep(0.45)
    command(["docker", "exec", CONTAINERS["sensor"], "pkill", "-2", "tcpdump"], check=False)
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline and (not current_pcap.exists() or current_pcap.stat().st_size <= 24):
        time.sleep(0.1)
    if not current_pcap.exists() or current_pcap.stat().st_size <= 24:
        raise AssertionError("tcpdump did not create a non-empty PCAP")
    shutil.move(current_pcap, case_dir / "capture" / "traffic.pcap")
    shutil.copy2(current_result, case_dir / "generator-result.json")
    if auth_case:
        if not auth_current.is_file() or not auth_current.stat().st_size:
            raise AssertionError("authentication target did not write telemetry")
        shutil.copy2(auth_current, case_dir / "raw" / "auth.jsonl")
    container_case = f"/artifacts/runs/{campaign}/{slug}"
    command(["docker", "exec", CONTAINERS["zeek"], "sh", "-c", f"cd {container_case}/zeek && /usr/local/zeek/bin/zeek -C -r ../capture/traffic.pcap LogAscii::use_json=T"])
    conn_path = case_dir / "zeek" / "conn.log"
    if not conn_path.is_file() or not conn_path.stat().st_size:
        raise AssertionError("real Zeek did not create conn.log")
    events, observation, raw = normalize(case_dir, generator_ip, target_ip, auth_case)
    adapter = SessionFeatureAdapter()
    envelope, legacy_provenance = adapter.extract_window(case_dir / "zeek", f"{campaign}-{slug}", 0)
    features = build_feature_bundle(observation, events, legacy_values=list(envelope["features"].values()))
    detection, explanation = detect(features)
    execution = json.loads((case_dir / "generator-result.json").read_text(encoding="utf-8"))
    definition = next(row for row in validate_wave1_registry()["scenarios"] if row["scenario_id"] == scenario)
    sealed_ground_truth = {
        "classification": "sealed_engineering_comparison_only",
        "scenario_id": scenario,
        "taxonomy_node_id": definition["taxonomy_node_id"],
        "realization_id": execution["realization"]["realization_id"],
    }
    _write(case_dir / "sealed-ground-truth.json", sealed_ground_truth)
    started = datetime.fromisoformat(execution["execution"]["started_at"].replace("Z", "+00:00")).timestamp()
    finished = datetime.fromisoformat(execution["execution"]["finished_at"].replace("Z", "+00:00")).timestamp()
    conn_rows = [row for row in parse_zeek_log(conn_path) if row.get("id.orig_h") == generator_ip and row.get("id.resp_h") == target_ip]
    timestamps = [float(row["ts"]) for row in conn_rows]
    packets = sum(int(row.get("orig_pkts") or 0) + int(row.get("resp_pkts") or 0) for row in conn_rows)
    if min(timestamps) < started - 2 or max(timestamps) > finished + 2 or packets <= 0:
        raise AssertionError("capture timestamps or packet counts are not consistent with execution")
    if features["observation_ref"]["canonical_digest"] != observation["canonical_digest"] or detection["feature_bundle_ref"]["canonical_digest"] != features["canonical_digest"]:
        raise AssertionError("observation-feature-detection provenance chain is broken")
    _write(case_dir / "normalized-events.json", events)
    _write(case_dir / "observation-bundle.json", observation)
    _write(case_dir / "feature-bundle.json", features)
    _write(case_dir / "detection-result.json", detection)
    _write(case_dir / "explanation-bundle.json", explanation)
    _write(case_dir / "diagnostics.json", {"legacy_network_v2": legacy_provenance, "assertions": {"pcap_nonempty": True, "real_zeek_conn_log": True, "generator_target_flow": True, "execution_time_aligned": True, "positive_packet_count": True, "provenance_chain": True}})
    http_rows = parse_zeek_log(case_dir / "zeek" / "http.log") if (case_dir / "zeek" / "http.log").is_file() else []
    ordered_conn = sorted(conn_rows, key=lambda row: float(row["ts"]))
    target_counts = Counter(f"{row['id.resp_h']}:{row['id.resp_p']}" for row in conn_rows)
    metrics = {
        "packet_count": packets, "connection_count": len(conn_rows),
        "timing_seconds": max(timestamps) - min(timestamps) if len(timestamps) > 1 else 0.0,
        "target_distribution": dict(sorted(target_counts.items())),
        "request_pattern": [row.get("uri") for row in http_rows] or [int(row["id.resp_p"]) for row in ordered_conn],
    }
    manifest = {
        "classification": "disposable_engineering_integration", "run_id": f"{campaign}/{slug}", "scenario": scenario, "generator_family": generator,
        "realization_digest": execution["realization"]["canonical_digest"], "container_image_ids": _image_ids(), "docker_network": NETWORK,
        "target_capabilities": execution["target_capabilities"], "started_at": execution["execution"]["started_at"], "finished_at": execution["execution"]["finished_at"],
        "pcap_sha256": raw["pcap"]["sha256"], "zeek_log_digests": {Path(row["locator"]).name: row["sha256"] for row in raw["logs"] if "/zeek/" in row["locator"]},
        "observation_bundle_digest": observation["canonical_digest"], "feature_bundle_digest": features["canonical_digest"], "detection_result_digest": detection["canonical_digest"],
        "event_counts": {kind: sum(row["event_type"] == kind for row in events) for kind in sorted({row["event_type"] for row in events})},
        "feature_group_status": {row["group_id"]: row["status"] for row in features["groups"]}, "detection": detection["stages"], "engineering_trace": metrics,
        "sealed_ground_truth": {"locator": f"{case_locator}/sealed-ground-truth.json", "sha256": sha256(case_dir / "sealed-ground-truth.json")},
        "cleanup_status": "artifacts_saved_environment_running",
    }
    _write(case_dir / "manifest.json", manifest)
    return manifest


def run_matrix(campaign: str | None = None) -> Path:
    campaign = campaign or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    campaign_dir = ARTIFACT_ROOT / "runs" / campaign
    if campaign_dir.exists():
        raise FileExistsError(campaign_dir)
    results = [run_case(campaign, slug, scenario, generator, 1701 + index) for index, (slug, scenario, generator) in enumerate(MATRIX)]
    by_slug = {row["run_id"].split("/")[-1]: row for row in results}
    pairs = {"recon": ("recon-a-sequential", "recon-b-randomized"), "credential": ("credential-a-brute", "credential-b-spray"), "beacon": ("beacon-a-periodic", "beacon-b-jittered")}
    comparisons = {}
    for family, (left, right) in pairs.items():
        a, b = by_slug[left]["engineering_trace"], by_slug[right]["engineering_trace"]
        differences = [key for key in a if a[key] != b[key]]
        if not differences:
            raise AssertionError(f"{family} generator families produced identical engineering traces")
        comparisons[family] = {"family_a": a, "family_b": b, "different_fields": differences, "classification": "engineering_trace_comparison_not_scientific_metric"}
    summary = {"campaign": campaign, "classification": "engineering_only", "scenario_count": len(results), "runs": [row["run_id"] for row in results], "a_b_comparisons": comparisons}
    _write(campaign_dir / "summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return campaign_dir


def _sequence_context(graph: dict[str, Any], observations: list[dict[str, Any]], kind: str | None) -> dict[str, Any] | None:
    if kind is None: return None
    subject = next(node["node_id"] for node in graph["nodes"] if node.get("entity_type") == "ip")
    timestamp = observations[-1]["window"]["end"]
    fact_types = ["expected_communication_relationship"]
    if kind == "approved_scanner": fact_types += ["approved_scanner_role", "maintenance_window"]
    else: fact_types += ["monitoring_system_role"]
    facts = [build_context_fact(subject, fact_type, True, source="docker_lab_declared_context", provenance={"record_ref":f"context/{index}"}, trust="DECLARED_HIGH_TRUST", first_seen=timestamp, last_seen=timestamp) for index, fact_type in enumerate(fact_types)]
    return build_context_profile(facts, timestamp)


def _correlate_docker_sequence(campaign_dir: Path, sealed_name: str, context_kind: str | None) -> dict[str, Any]:
    case_dirs = [campaign_dir / "window-001", campaign_dir / "window-002"]
    events = [json.loads((path / "normalized-events.json").read_text(encoding="utf-8")) for path in case_dirs]
    observations = [json.loads((path / "observation-bundle.json").read_text(encoding="utf-8")) for path in case_dirs]
    old_features = [json.loads((path / "feature-bundle.json").read_text(encoding="utf-8")) for path in case_dirs]
    detections = [json.loads((path / "detection-result.json").read_text(encoding="utf-8")) for path in case_dirs]
    manifests = [json.loads((path / "manifest.json").read_text(encoding="utf-8")) for path in case_dirs]
    docker_refs = [{"run_id":row["run_id"],"pcap_sha256":row["pcap_sha256"],"zeek_log_digests":row["zeek_log_digests"],"observation_digest":row["observation_bundle_digest"],"feature_bundle_digest":row["feature_bundle_digest"],"detection_result_digest":row["detection_result_digest"],"image_ids":row["container_image_ids"]} for row in manifests]
    graph = build_interaction_graph(observations, events, detections, docker_evidence_refs=docker_refs)
    context = _sequence_context(graph, observations, context_kind)
    contextual_features=[]; contextual_detections=[]; history=[]
    for case_dir, observation, window_events, old in zip(case_dirs, observations, events, old_features):
        legacy = next(group for group in old["groups"] if group["group_id"] == "legacy_network_v2")
        legacy_values = [legacy["values"][name] for name in legacy["ordered_feature_names"]] if legacy["status"] == "AVAILABLE" else None
        bundle = build_feature_bundle(observation, window_events, legacy_values=legacy_values, historical_events=history, interaction_graph=graph)
        local, explanation = detect(bundle)
        _write(case_dir / "context-feature-bundle.json", bundle); _write(case_dir / "context-local-detection.json", local); _write(case_dir / "context-local-explanation.json", explanation)
        contextual_features.append(bundle); contextual_detections.append(local); history += window_events
    result = correlate(observations, contextual_features, contextual_detections, graph, context)
    attack = map_attack_evidence(result); chain = build_attack_chain(result); incident = build_incident_candidate(result, attack, chain)
    reasoning_graph = attach_reasoning_nodes(graph, result, incident)
    output_dir = campaign_dir / "correlation"; output_dir.mkdir()
    _write(output_dir / "interaction-graph.json", graph)
    _write(output_dir / "reasoning-graph.json", reasoning_graph)
    if context: _write(output_dir / "context-profile.json", context)
    _write(output_dir / "correlation-result.json", result); _write(output_dir / "attack-chain-hypothesis.json", chain)
    _write(output_dir / "attack-evidence-mapping.json", attack); _write(output_dir / "incident-candidate.json", incident)
    sealed = {"classification":"sealed_engineering_comparison_only","sequence_name":sealed_name,"window_manifests":[row["run_id"] for row in manifests]}
    _write(campaign_dir / "sealed-sequence-ground-truth.json", sealed)
    summary = {"sequence_run_id":campaign_dir.name,"window_count":2,"pcap_sha256":[row["pcap_sha256"] for row in manifests],"graph_digest":graph["canonical_digest"],"reasoning_graph_digest":reasoning_graph["canonical_digest"],"correlation_digest":result["canonical_digest"],"incident_digest":incident["canonical_digest"],"final_state":result["abstention"]["final_state"],"top_hypothesis":result["hypotheses"][0]["hypothesis_id"] if result["hypotheses"] else None,"attack_candidates":[row["technique_id"] for row in attack["candidates"]],"sealed_comparison_locator":"sealed-sequence-ground-truth.json"}
    _write(campaign_dir / "sequence-summary.json", summary)
    return summary


def run_multi_window_sequences() -> Path:
    root = ARTIFACT_ROOT / "multi-window" / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8])
    root.mkdir(parents=True)
    summaries=[]
    for index, (sealed_name, windows, context_kind) in enumerate(SEQUENCES):
        campaign = "mw-" + uuid.uuid4().hex[:12]
        for window_index, (scenario, generator) in enumerate(windows, 1):
            run_case(campaign, f"window-{window_index:03d}", scenario, generator, 4100 + index*10 + window_index)
            time.sleep(0.25)
        source_dir = ARTIFACT_ROOT / "runs" / campaign
        summaries.append(_correlate_docker_sequence(source_dir, sealed_name, context_kind))
    result={"classification":"docker_multi_window_engineering","sequence_count":len(summaries),"sequences":summaries}
    _write(root / "multi-window-summary.json", result); print(json.dumps(result,ensure_ascii=False,indent=2)); return root


def inspect_lab() -> dict[str, Any]:
    value = {
        "containers": command(["docker", "ps", "-a", "--filter", "name=filin-vnext-", "--format", "{{.Names}}\t{{.Image}}\t{{.Status}}"], capture=True).splitlines(),
        "network": command(["docker", "network", "inspect", NETWORK, "--format", "{{.Name}} internal={{.Internal}} driver={{.Driver}}"], capture=True, check=False).strip(),
        "images": command(["docker", "images", "--filter", "reference=filin-vnext-dev/*", "--format", "{{.Repository}}:{{.Tag}}\t{{.ID}}\t{{.Size}}"], capture=True).splitlines(),
        "artifact_root": str(ARTIFACT_ROOT),
    }
    print(json.dumps(value, ensure_ascii=False, indent=2))
    return value


def down() -> None:
    compose("down", "--remove-orphans", check=False)
    manifests = list(ARTIFACT_ROOT.glob("runs/*/*/manifest.json")) + list(ARTIFACT_ROOT.glob("multi-window/*/*/window-*/manifest.json"))
    for manifest_path in manifests:
        value = json.loads(manifest_path.read_text(encoding="utf-8"))
        if value.get("cleanup_status") == "artifacts_saved_environment_running":
            value["cleanup_status"] = "containers_and_network_removed_artifacts_saved"
            _write(manifest_path, value)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("up", "run", "run-sequences", "inspect", "down"))
    parser.add_argument("--campaign")
    args = parser.parse_args()
    available, reason = docker_available()
    if not available:
        raise SystemExit(f"Docker unavailable: {reason}")
    if args.action == "up": up()
    elif args.action == "run": run_matrix(args.campaign)
    elif args.action == "run-sequences": run_multi_window_sequences()
    elif args.action == "inspect": inspect_lab()
    else: down()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

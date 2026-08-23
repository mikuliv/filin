from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from ml.experiments.v0_3_15_4.feature_v2 import FEATURES

from .capture import build_capture_manifest, pcap_summary
from .contracts import (
    ContractError,
    canonical_bytes,
    load_json,
    validate_event,
    write_canonical,
)
from .feature_adapter import SessionFeatureAdapter
from .parameter_verification import observations_from_zeek, verify_parameters
from .phase1_runtime import (
    SessionIdentity,
    SessionPaths,
    build_session_integrity_manifest,
    resolve_next_unit,
    runtime_contract_digest,
    session_identity,
    session_paths,
    validate_campaign_initialization,
    validate_feature_row,
    validate_runtime_contract,
    validate_session_integrity_manifest,
    validate_unused_paths,
)
from .pipeline import _stop_capture_gracefully, _wait_for_capture_ready

ROOT = Path(__file__).resolve().parents[2]
CAMPAIGN_PATH = Path(__file__).with_name("config") / "superseding_freeze_campaign.json"
RETRYABLE = {
    "docker_daemon_transient_failure",
    "container_start_failure",
    "target_healthcheck_failure",
    "capture_start_failure",
    "capture_integrity_failure",
    "host_io_failure",
    "processing_integrity_failure",
}


class SessionBlocked(ContractError):
    pass


class TechnicalFailure(RuntimeError):
    def __init__(self, reason_code: str, message: str) -> None:
        if reason_code not in RETRYABLE:
            raise ValueError(f"unsupported technical failure reason: {reason_code}")
        super().__init__(message)
        self.reason_code = reason_code


def _run(command: list[str], *, check: bool = True, text: bool = True) -> subprocess.CompletedProcess[Any]:
    result = subprocess.run(command, capture_output=True, text=text, check=False)
    if check and result.returncode:
        stderr = result.stderr.strip() if text else ""
        raise RuntimeError(stderr or f"command failed with exit code {result.returncode}: {command[0]}")
    return result


def _json_rows(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = b"".join(canonical_bytes(row) + b"\n" for row in rows)
    with path.open("xb") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())


def _container_name(namespace: str, role: str) -> str:
    return f"{namespace}-{role}"


@dataclass
class RuntimeHandles:
    identity: SessionIdentity
    paths: SessionPaths
    scenario: dict[str, Any]
    scenario_entry: dict[str, Any]
    network: str
    target: str
    client: str
    sensor: str
    client_ip: str
    target_ip: str
    clock_probes: list[dict[str, Any]]


class Phase1DockerRunner:
    """Execute exactly one frozen Phase 1 unit using only locked local images."""

    def __init__(
        self,
        package: dict[str, Any],
        output_root: Path,
        secret_root: Path,
        *,
        expected_secret_fingerprint: str | None = None,
    ) -> None:
        self.package = package
        self.output_root = output_root.resolve()
        self.secret_root = secret_root.resolve()
        self.contract = validate_runtime_contract()
        self._validate_campaign_roots()
        if package.get("phase1_runtime_contract_digest") != runtime_contract_digest():
            raise SessionBlocked("SESSION_BLOCKED_RUNTIME_CONTRACT_BINDING")
        self.ledger, self.mapping = validate_campaign_initialization(
            package, self.output_root, self.secret_root, expected_secret_fingerprint
        )
        self._scenario_entries = self._load_scenario_entries()

    def _validate_campaign_roots(self) -> None:
        repository = ROOT.resolve()
        if self.output_root.is_relative_to(repository) or self.secret_root.is_relative_to(repository):
            raise SessionBlocked("SESSION_BLOCKED_RUNTIME_ROOT_IN_REPOSITORY")
        if (
            self.output_root == self.secret_root
            or self.output_root.is_relative_to(self.secret_root)
            or self.secret_root.is_relative_to(self.output_root)
        ):
            raise SessionBlocked("SESSION_BLOCKED_RUNTIME_ROOT_OVERLAP")
        package_id = self.package.get("package_id")
        if self.output_root.name != package_id or self.secret_root.name != package_id:
            raise SessionBlocked("SESSION_BLOCKED_RUNTIME_ROOT_IDENTITY")

    def _load_scenario_entries(self) -> dict[str, dict[str, Any]]:
        campaign = load_json(CAMPAIGN_PATH)
        entries: dict[str, dict[str, Any]] = {}

        def visit(value: Any) -> None:
            if isinstance(value, dict):
                scenario = value.get("scenario")
                if isinstance(scenario, dict) and scenario.get("scenario_token"):
                    token = scenario["scenario_token"]
                    if token in entries:
                        raise ContractError("duplicate scenario token")
                    entries[token] = value
                for item in value.values():
                    visit(item)
            elif isinstance(value, list):
                for item in value:
                    visit(item)

        visit(campaign)
        return entries

    def _unit_scenario(self, unit: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
        entry = self._scenario_entries.get(unit["scenario_token"])
        if entry is None:
            raise SessionBlocked("SESSION_BLOCKED_SCENARIO_IDENTITY")
        scenario = json.loads(json.dumps(entry["scenario"]))
        scenario["seed"] = unit["execution_seed"]
        return scenario, entry

    def _image_inventory(self) -> dict[str, str]:
        identities: dict[str, str] = {}
        for logical, lock in self.contract["runtime_images"].items():
            if logical in {"build_allowed", "pull_allowed_when_present", "retag_required"}:
                continue
            inspected = _run(["docker", "image", "inspect", lock["reference"]]).stdout
            row = json.loads(inspected)[0]
            descriptor = row.get("Descriptor", {}).get("digest")
            expected = lock.get("index_manifest_digest", lock["platform_manifest_digest"])
            if descriptor != expected:
                raise SessionBlocked(f"SESSION_BLOCKED_IMAGE_IDENTITY:{logical}")
            identities[logical] = lock["platform_manifest_digest"]
        return identities

    def _namespace_available(self, namespace: str) -> None:
        checks = [
            ["docker", "ps", "-a", "--filter", f"name={namespace}", "--format", "{{.ID}}"],
            ["docker", "network", "ls", "--filter", f"name={namespace}", "--format", "{{.ID}}"],
            ["docker", "volume", "ls", "--filter", f"name={namespace}", "--format", "{{.Name}}"],
        ]
        if any(_run(command).stdout.strip() for command in checks):
            raise SessionBlocked("SESSION_BLOCKED_EXISTING_RUNTIME_STATE")

    def _prepare_staging(self, paths: SessionPaths, scenario: dict[str, Any]) -> Path:
        validate_unused_paths(paths)
        paths.staging.mkdir(parents=True, exist_ok=False)
        runtime = paths.staging / ".runtime"
        runtime.mkdir()
        write_canonical(runtime / "scenario.json", scenario)
        (paths.staging / "capture").mkdir()
        (paths.staging / "zeek").mkdir()
        return runtime

    def _docker_mount(self, host: Path, container: str, read_only: bool = False) -> str:
        suffix = ":ro" if read_only else ""
        return f"{host.resolve()}:{container}{suffix}"

    def _start_preflight_runtime(
        self,
        identity: SessionIdentity,
        paths: SessionPaths,
        scenario: dict[str, Any],
        entry: dict[str, Any],
    ) -> RuntimeHandles:
        namespace = identity.runtime_namespace
        self._namespace_available(namespace)
        runtime = self._prepare_staging(paths, scenario)
        network = f"{namespace}-network"
        target = _container_name(namespace, "target")
        client = _container_name(namespace, "client")
        sensor = _container_name(namespace, "sensor")
        target_logical = entry["target_implementation"]
        target_lock = self.contract["runtime_images"][target_logical]
        client_lock = self.contract["runtime_images"]["common_client"]
        sensor_lock = self.contract["runtime_images"]["sensor_capture"]
        try:
            _run(["docker", "network", "create", "--internal", network])
            _run([
                "docker", "run", "-d", "--name", target, "--network", network,
                "--network-alias", "validation-target", "--cap-drop", "ALL",
                "--security-opt", "no-new-privileges", target_lock["reference"],
                "--port", str(entry["target_port"]),
            ])
            _run([
                "docker", "run", "-d", "--name", client, "--network", network,
                "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
                "-v", self._docker_mount(runtime / "scenario.json", "/config/scenario.json", True),
                "-v", self._docker_mount(paths.staging, "/output"),
                "--entrypoint", "python", client_lock["reference"],
                "-c", "import time; time.sleep(86400)",
            ])
        except Exception as error:
            raise SessionBlocked("SESSION_BLOCKED_CONTAINER_START") from error
        health = (
            "import urllib.request; "
            f"urllib.request.urlopen('http://validation-target:{entry['target_port']}/health', timeout=2).read()"
        )
        for _ in range(20):
            if _run(["docker", "exec", client, "python", "-c", health], check=False).returncode == 0:
                break
            time.sleep(0.25)
        else:
            raise SessionBlocked("SESSION_BLOCKED_TARGET_HEALTHCHECK")
        time.sleep(float(self._policy_value("warmup_seconds")))
        try:
            _run([
                "docker", "run", "-d", "--name", sensor, "--network", f"container:{client}",
                "--cap-drop", "ALL", "--cap-add", "NET_RAW", "--cap-add", "NET_ADMIN",
                "--cap-add", "SETUID", "--cap-add", "SETGID", "--security-opt", "no-new-privileges",
                "-v", self._docker_mount(paths.staging / "capture", "/capture"), sensor_lock["reference"],
                "-i", str(scenario["capture_policy"]["interface"]), "-B", "4096", "--immediate-mode", "-U",
                "-Z", "root", "-w", "/capture/traffic.pcap", *str(scenario["capture_policy"]["bpf"]).split(),
            ])
            _wait_for_capture_ready(sensor, "/capture/traffic.pcap")
        except Exception as error:
            raise SessionBlocked("SESSION_BLOCKED_CAPTURE_START") from error
        client_ip = self._container_ip(client, network)
        target_ip = self._container_ip(target, network)
        probes = self._clock_preflight(namespace, client, target, sensor)
        time.sleep(float(self._policy_value("capture_start_lead_seconds")))
        return RuntimeHandles(identity, paths, scenario, entry, network, target, client, sensor, client_ip, target_ip, probes)

    def _policy_value(self, key: str) -> float:
        policy = load_json(Path(__file__).with_name("config") / "superseding_execution_policy.json")
        return float(policy[key])

    def _container_ip(self, container: str, network: str) -> str:
        template = '{{with index .NetworkSettings.Networks "' + network + '"}}{{.IPAddress}}{{end}}'
        value = _run(["docker", "inspect", "--format", template, container]).stdout.strip()
        if not value:
            raise SessionBlocked("SESSION_BLOCKED_RUNTIME_NETWORK")
        return value

    def _clock_probe(self, participant: str, command: list[str]) -> dict[str, Any]:
        before = time.time_ns()
        result = _run(command).stdout.strip()
        after = time.time_ns()
        try:
            container_ns = int(result)
        except ValueError as error:
            raise SessionBlocked("SESSION_BLOCKED_CLOCK_PREFLIGHT") from error
        tolerance = int(self.contract["clock_preflight"]["maximum_wall_clock_offset_ms"] * 1_000_000)
        passed = before - tolerance <= container_ns <= after + tolerance
        if not passed:
            raise SessionBlocked("SESSION_BLOCKED_CLOCK_PREFLIGHT")
        return {
            "participant": participant,
            "host_before_ns": before,
            "container_ns": container_ns,
            "host_after_ns": after,
            "midpoint_offset_ms": (container_ns - ((before + after) / 2)) / 1_000_000,
            "contract_violation_ms": 0.0,
            "passed": True,
        }

    def _clock_preflight(self, namespace: str, client: str, target: str, sensor: str) -> list[dict[str, Any]]:
        image = self.contract["runtime_images"]["common_client"]["reference"]
        probes = [
            self._clock_probe("docker_vm_reference", [
                "docker", "run", "--rm", "--name", f"{namespace}-clock", "--network", "none",
                "--cap-drop", "ALL", "--security-opt", "no-new-privileges", "--entrypoint", "python",
                image, "-c", "import time; print(time.time_ns())",
            ]),
            self._clock_probe("common_client", ["docker", "exec", client, "python", "-c", "import time; print(time.time_ns())"]),
            self._clock_probe("target", ["docker", "exec", target, "python", "-c", "import time; print(time.time_ns())"]),
            self._clock_probe("sensor_capture", ["docker", "exec", sensor, "date", "+%s%N"]),
        ]
        if [row["container_ns"] for row in probes] != sorted(row["container_ns"] for row in probes):
            raise SessionBlocked("SESSION_BLOCKED_CLOCK_PREFLIGHT")
        return probes

    def preflight_one(self) -> dict[str, Any]:
        unit = resolve_next_unit(self.ledger)
        attempts = self.ledger.attempts_for(unit["execution_token"])
        if attempts >= 2:
            raise SessionBlocked("SESSION_BLOCKED_RETRY_LIMIT")
        identity = session_identity(self.package, unit, attempts + 1)
        paths = session_paths(self.output_root, identity)
        scenario, entry = self._unit_scenario(unit)
        images = self._image_inventory()
        handles: RuntimeHandles | None = None
        try:
            handles = self._start_preflight_runtime(identity, paths, scenario, entry)
            return {
                "per_session_preflight_passed": True,
                "execution_token": identity.execution_token,
                "attempt_number": identity.attempt_number,
                "runtime_namespace": identity.runtime_namespace,
                "images": images,
                "clock_probes": handles.clock_probes,
                "capture_ready": True,
            }
        finally:
            if handles is not None:
                self._cleanup_runtime(handles)
            else:
                self._cleanup_namespace(identity.runtime_namespace)
            self._remove_preflight_staging(paths)

    def run_one(self, confirmed_execution_token: str) -> dict[str, Any]:
        completed_before = len(self.ledger.completed_tokens())
        unit = resolve_next_unit(self.ledger)
        if unit["execution_token"] != confirmed_execution_token:
            raise SessionBlocked("SESSION_BLOCKED_EXECUTION_TOKEN_CONFIRMATION")
        images = self._image_inventory()
        while True:
            attempts = self.ledger.attempts_for(unit["execution_token"])
            if attempts >= 2:
                raise SessionBlocked("SESSION_BLOCKED_RETRY_LIMIT")
            identity = session_identity(self.package, unit, attempts + 1)
            paths = session_paths(self.output_root, identity)
            scenario, entry = self._unit_scenario(unit)
            handles: RuntimeHandles | None = None
            started = False
            sealed = False
            completed_recorded = False
            try:
                handles = self._start_preflight_runtime(identity, paths, scenario, entry)
                self.ledger.append(identity, "session_started")
                started = True
                mapping_entry = self.mapping.ensure(identity.execution_token)
                self._execute_behavior(handles, mapping_entry["evaluation_token"], images)
                if paths.sealed.exists():
                    raise TechnicalFailure("host_io_failure", "sealed attempt path already exists")
                paths.staging.replace(paths.sealed)
                sealed = True
                self.ledger.append(identity, "session_completed")
                completed_recorded = True
                completed_after = len(self.ledger.completed_tokens())
                if completed_after != completed_before + 1:
                    raise ContractError("unit completion stop gate mismatch")
                try:
                    next_unit = resolve_next_unit(self.ledger)
                    next_execution_token: str | None = next_unit["execution_token"]
                except ContractError as error:
                    if str(error) != "phase1 run plan is already complete":
                        raise
                    next_execution_token = None
                return {
                    "terminal_status": "sealed_success",
                    "attempts": identity.attempt_number,
                    "retry_used": identity.attempt_number == 2,
                    "execution_token": identity.execution_token,
                    "session_token": identity.session_token,
                    "sealed_path": str(paths.sealed),
                    "next_execution_token": next_execution_token,
                    "next_unit_started": False,
                }
            except SessionBlocked:
                if started and not sealed and not completed_recorded:
                    self.ledger.append(identity, "session_failed", reason_code="host_io_failure")
                    self._retain_failed_attempt(paths)
                raise
            except TechnicalFailure as error:
                if completed_recorded:
                    raise
                if sealed:
                    raise SessionBlocked("SESSION_BLOCKED_LEDGER_FINALIZATION") from error
                if started:
                    self.ledger.append(identity, "session_failed", reason_code=error.reason_code)
                    self._retain_failed_attempt(paths)
                    if identity.attempt_number == 1 and error.reason_code in RETRYABLE:
                        self.ledger.append(identity, "retry_requested", reason_code=error.reason_code)
                        continue
                raise
            except Exception as error:
                if completed_recorded:
                    raise
                if sealed:
                    raise SessionBlocked("SESSION_BLOCKED_LEDGER_FINALIZATION") from error
                if started:
                    self.ledger.append(identity, "session_failed", reason_code="host_io_failure")
                    self._retain_failed_attempt(paths)
                raise TechnicalFailure("host_io_failure", str(error)) from error
            finally:
                if handles is not None:
                    self._cleanup_runtime(handles)
                else:
                    self._cleanup_namespace(identity.runtime_namespace)
                if not started:
                    self._remove_preflight_staging(paths)

    def recover_sealed_completion(self, confirmed_attempt_id: str) -> dict[str, Any]:
        active = self.ledger.active_tokens()
        if len(active) != 1:
            raise SessionBlocked("SESSION_BLOCKED_RECOVERY_ACTIVE_ATTEMPT")
        execution_token = next(iter(active))
        records = self.ledger.read()
        started = [
            record
            for record in records
            if record["execution_token"] == execution_token and record["event_type"] == "session_started"
        ]
        if not started or started[-1]["attempt_id"] != confirmed_attempt_id:
            raise SessionBlocked("SESSION_BLOCKED_RECOVERY_ATTEMPT_CONFIRMATION")
        unit = next(
            unit
            for unit in load_json(Path(__file__).with_name("execution") / "phase1_run_plan.json")["ordered_execution_units"]
            if unit["execution_token"] == execution_token
        )
        identity = session_identity(self.package, unit, int(started[-1]["attempt_number"]))
        paths = session_paths(self.output_root, identity)
        if not paths.sealed.is_dir() or paths.staging.exists() or paths.failed.exists():
            raise SessionBlocked("SESSION_BLOCKED_RECOVERY_OUTPUT_STATE")
        mapping_rows = [row for row in self.mapping.read() if row["execution_token"] == execution_token]
        if len(mapping_rows) != 1:
            raise SessionBlocked("SESSION_BLOCKED_RECOVERY_MAPPING")
        images = self._image_inventory()
        manifest = load_json(paths.sealed / "session_integrity_manifest.json")
        validate_session_integrity_manifest(manifest, paths.sealed, self.package, identity, images)
        feature_rows = _json_rows(paths.sealed / "feature_rows.jsonl")
        if len(feature_rows) != 1:
            raise SessionBlocked("SESSION_BLOCKED_RECOVERY_FEATURE_ROWS")
        validate_feature_row(
            feature_rows[0], mapping_rows[0]["evaluation_token"], list(FEATURES), self.package
        )
        self._validate_exact_output_set(paths.sealed)
        self.ledger.append(identity, "session_completed")
        return {
            "terminal_status": "sealed_success_recovered",
            "execution_token": execution_token,
            "session_token": identity.session_token,
            "attempt_id": identity.attempt_id,
            "scientific_behavior_rerun": False,
            "containers_started": False,
        }

    def _execute_behavior(self, handles: RuntimeHandles, evaluation_token_value: str, images: dict[str, str]) -> None:
        target_port = handles.scenario_entry["target_port"]
        target_impl = handles.scenario_entry["target_implementation"]
        target_map = json.dumps({
            "web": f"http://validation-target:{target_port}",
            "api": f"http://validation-target:{target_port}",
            "control": f"http://validation-target:{target_port}",
            "multi_port": f"validation-target:{target_port}",
            "implementation": target_impl,
            "network_identity": handles.scenario_entry["docker_network"],
            "client_image_digest": images["common_client"],
            "target_image_digest": images[target_impl],
        }, separators=(",", ":"), sort_keys=True)
        result = _run([
            "docker", "exec", handles.client, "python", "-m", "lab.network_validation.common_client",
            "--scenario", "/config/scenario.json", "--target-map", target_map,
            "--output-dir", "/output/.runtime/client", "--capture-id", handles.identity.session_token,
        ], check=False)
        if result.returncode:
            raise TechnicalFailure("processing_integrity_failure", "scientific client process failed")
        time.sleep(float(self._policy_value("capture_stop_lag_seconds")))
        try:
            _stop_capture_gracefully(handles.sensor)
        except Exception as error:
            raise TechnicalFailure("capture_integrity_failure", "capture did not stop and flush cleanly") from error
        time.sleep(float(self._policy_value("cooldown_seconds")))
        self._process_outputs(handles, evaluation_token_value, images)

    def _process_outputs(self, handles: RuntimeHandles, evaluation_token_value: str, images: dict[str, str]) -> None:
        paths = handles.paths
        runtime_client = paths.staging / ".runtime" / "client"
        try:
            execution = load_json(runtime_client / "execution_event.json")
            markers = load_json(runtime_client / "marker_events.json")
            validate_event(execution, "execution")
            if not isinstance(markers, list) or {row.get("marker_type") for row in markers} != {"start", "end"}:
                raise ContractError("marker pair missing")
            for marker in markers:
                validate_event(marker, "marker")
            write_canonical(paths.staging / "execution_event.json", execution)
            _write_jsonl(paths.staging / "marker_events.jsonl", markers)
        except Exception as error:
            raise TechnicalFailure("processing_integrity_failure", "client output validation failed") from error
        pcap = paths.staging / "capture" / "traffic.pcap"
        try:
            summary = pcap_summary(pcap)
            if summary["byte_count"] <= 24 or summary["packet_count"] <= 0:
                raise ContractError("PCAP_HEADER_ONLY")
        except Exception as error:
            raise TechnicalFailure("capture_integrity_failure", "PCAP integrity failed") from error
        self._run_zeek(paths)
        conn = _json_rows(paths.staging / "zeek" / "conn.log")
        endpoint = [
            row for row in conn
            if row.get("proto") == "tcp"
            and row.get("id.orig_h") == handles.client_ip
            and row.get("id.resp_h") == handles.target_ip
            and int(row.get("id.resp_p", 0) or 0) == handles.scenario_entry["target_port"]
        ]
        if not conn or not endpoint:
            raise TechnicalFailure("processing_integrity_failure", "expected client-to-target flow missing from Zeek conn.log")
        model_zeek = self._prepare_model_input_zeek(paths)
        start = datetime.fromisoformat(markers[0]["wall_clock_timestamp"].replace("Z", "+00:00")).timestamp()
        end = datetime.fromisoformat(markers[-1]["wall_clock_timestamp"].replace("Z", "+00:00")).timestamp()
        try:
            parameter = verify_parameters(
                handles.scenario,
                observations_from_zeek(model_zeek),
                self.contract["parameter_realization"]["tolerances"],
            )
            write_canonical(paths.staging / "parameter_realization.json", parameter)
            capture_manifest = build_capture_manifest({
                "capture_id": handles.identity.session_token,
                "campaign_token": handles.scenario["campaign_token"],
                "scenario_token": handles.identity.scenario_token,
                "session_token": handles.identity.session_token,
                "generator_family": handles.scenario["generator_family"],
                "infrastructure_profile": handles.scenario["infrastructure_profile"],
                "sensor_identity": "sensor-capture",
                "docker_network_identity": handles.scenario_entry["docker_network"],
                "capture_start": start,
                "capture_end": end,
                "source_container": "common-client",
                "target_container": handles.scenario_entry["target_implementation"],
                "pcap_path": "capture/traffic.pcap",
                "zeek_status": "completed",
                "execution_status": execution["execution_status"],
                "marker_association": markers[0]["marker_nonce"],
                "parameter_verification_status": parameter["status"],
            }, paths.staging, execution)
            write_canonical(paths.staging / "capture" / "capture_manifest.json", capture_manifest)
        except Exception as error:
            raise TechnicalFailure("processing_integrity_failure", "capture manifest validation failed") from error
        try:
            envelope, _ = SessionFeatureAdapter().extract_window(model_zeek, handles.identity.session_token, 0)
            feature_row = {
                "schema_version": "network_validation_phase1_feature_row_v1",
                "evaluation_token": evaluation_token_value,
                "feature_contract_digest": self.package["feature_contract_digest"],
                "feature_order_digest": self.package["feature_order_digest"],
                "feature_row": [envelope["features"][name] for name in FEATURES],
            }
            validate_feature_row(feature_row, evaluation_token_value, list(FEATURES), self.package)
            _write_jsonl(paths.staging / "feature_rows.jsonl", [feature_row])
        except Exception as error:
            raise TechnicalFailure("processing_integrity_failure", "parameter or feature processing failed") from error
        runtime = paths.staging / ".runtime"
        if runtime.exists():
            shutil.rmtree(runtime)
        manifest = build_session_integrity_manifest(
            paths.staging, self.package, handles.identity, images
        )
        write_canonical(paths.staging / "session_integrity_manifest.json", manifest)
        validate_session_integrity_manifest(
            load_json(paths.staging / "session_integrity_manifest.json"),
            paths.staging, self.package, handles.identity, images,
        )
        self._validate_exact_output_set(paths.staging)
        self._flush_attempt_files(paths.staging)

    def _run_zeek(self, paths: SessionPaths) -> None:
        lock = self.contract["runtime_images"]["zeek"]
        command = (
            "set -eu; cd /zeek; zeek -C -r /capture/traffic.pcap LogAscii::use_json=T; "
            "test -f conn.log; test -f http.log || : > http.log; test -f dns.log || : > dns.log"
        )
        result = _run([
            "docker", "run", "--rm", "--network", "none", "--cap-drop", "ALL",
            "--security-opt", "no-new-privileges", "-v", self._docker_mount(paths.staging / "capture", "/capture", True),
            "-v", self._docker_mount(paths.staging / "zeek", "/zeek"), "--entrypoint", "bash",
            lock["reference"], "-lc", command,
        ], check=False)
        if result.returncode:
            raise TechnicalFailure("processing_integrity_failure", "Zeek processing failed")

    def _prepare_model_input_zeek(self, paths: SessionPaths) -> Path:
        source = paths.staging / "zeek"
        destination = paths.staging / ".runtime" / "model-zeek"
        http = _json_rows(source / "http.log")
        marker_prefix = self.contract["model_input_filter"]["marker_http_uri_prefix"]
        marker_uids = {
            str(row["uid"])
            for row in http
            if row.get("uid") and str(row.get("uri", "")).startswith(marker_prefix)
        }
        scenario_uids = {
            str(row["uid"])
            for row in http
            if row.get("uid") and not str(row.get("uri", "")).startswith(marker_prefix)
        }
        if marker_uids & scenario_uids:
            raise TechnicalFailure("processing_integrity_failure", "marker and scenario HTTP share a Zeek UID")
        conn = [row for row in _json_rows(source / "conn.log") if str(row.get("uid", "")) not in marker_uids]
        filtered_http = [row for row in http if not str(row.get("uri", "")).startswith(marker_prefix)]
        dns = _json_rows(source / "dns.log")
        if not conn:
            raise TechnicalFailure("processing_integrity_failure", "marker filtering removed every Zeek connection")
        destination.mkdir(parents=True, exist_ok=False)
        _write_jsonl(destination / "conn.log", conn)
        _write_jsonl(destination / "http.log", filtered_http)
        _write_jsonl(destination / "dns.log", dns)
        return destination

    def _cleanup_runtime(self, handles: RuntimeHandles) -> None:
        for container in (handles.sensor, handles.client, handles.target):
            _run(["docker", "rm", "-f", container], check=False)
        _run(["docker", "network", "rm", handles.network], check=False)

    def _cleanup_namespace(self, namespace: str) -> None:
        ids = _run(["docker", "ps", "-aq", "--filter", f"name={namespace}"], check=False).stdout.split()
        for container in ids:
            _run(["docker", "rm", "-f", container], check=False)
        networks = _run(["docker", "network", "ls", "-q", "--filter", f"name={namespace}"], check=False).stdout.split()
        for network in networks:
            _run(["docker", "network", "rm", network], check=False)

    def _remove_preflight_staging(self, paths: SessionPaths) -> None:
        if paths.staging.exists():
            if paths.staging.parent != paths.session_root or not paths.staging.name.startswith(".attempt-"):
                raise ContractError("unsafe preflight staging cleanup target")
            shutil.rmtree(paths.staging)
        if paths.session_root.exists() and not any(paths.session_root.iterdir()):
            paths.session_root.rmdir()
        sessions = paths.session_root.parent
        if sessions.exists() and not any(sessions.iterdir()):
            sessions.rmdir()

    def _retain_failed_attempt(self, paths: SessionPaths) -> None:
        if paths.staging.exists():
            if paths.failed.exists():
                raise ContractError("failed attempt path already exists")
            paths.staging.replace(paths.failed)

    def _validate_exact_output_set(self, attempt_root: Path) -> None:
        expected = set(self.contract["artifact_schemas"])
        actual = {
            path.relative_to(attempt_root).as_posix()
            for path in attempt_root.rglob("*")
            if path.is_file()
        }
        if actual != expected:
            missing = sorted(expected - actual)
            unexpected = sorted(actual - expected)
            raise TechnicalFailure(
                "processing_integrity_failure",
                f"attempt output set mismatch: missing={missing}, unexpected={unexpected}",
            )
        if any(path.is_symlink() for path in attempt_root.rglob("*")):
            raise TechnicalFailure("processing_integrity_failure", "attempt output contains a symbolic link")

    def _flush_attempt_files(self, attempt_root: Path) -> None:
        for path in sorted(item for item in attempt_root.rglob("*") if item.is_file()):
            with path.open("rb") as stream:
                os.fsync(stream.fileno())

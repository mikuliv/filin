"""Apply bounded container network conditions for a complete execution scope.

This module is future-only.  Historical campaign records are never rewritten.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterator, Protocol

import yaml


class EnvironmentSafetyError(ValueError):
    pass


class CommandRunner(Protocol):
    def __call__(self, command: list[str]) -> subprocess.CompletedProcess[str]: ...


SUPPORTED_CONDITION_FIELDS = {
    "latency_ms", "jitter_ms", "packet_loss_percent", "reordering_percent",
}
PROFILE_METADATA_FIELDS = {"profile_id", "description"}


@dataclass
class ConditionEvidence:
    status: str
    container: str
    interface: str
    compose_project: str
    network: str
    profile_id: str
    before: str
    applied_command: list[str]
    verification: str
    rollback_command: list[str]
    after_rollback: str = ""
    rollback_verified: bool = False
    unsupported_fields: list[str] = field(default_factory=list)
    measurements: dict[str, Any] = field(default_factory=dict)

    def public_record(self) -> dict[str, Any]:
        return asdict(self)


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=False, capture_output=True, text=True, encoding="utf-8")


def _safe_identity(value: str, kind: str) -> str:
    if not value or not re.fullmatch(r"[A-Za-z0-9_.-]+", value):
        raise EnvironmentSafetyError(f"unsafe {kind}")
    return value


def choose_value(value: Any, seed: int) -> float:
    if isinstance(value, list):
        if len(value) != 2:
            raise EnvironmentSafetyError("condition range must contain two endpoints")
        low, high = map(float, value)
        if low > high:
            raise EnvironmentSafetyError("condition range is reversed")
        fraction = (seed % 10001) / 10000
        return low + (high - low) * fraction
    return float(value or 0)


def resolved_conditions(profile: dict[str, Any], seed: int) -> dict[str, float]:
    values = {
        "latency_ms": choose_value(profile.get("latency_ms", 0), seed),
        "jitter_ms": choose_value(profile.get("jitter_ms", 0), seed + 1),
        "packet_loss_percent": choose_value(profile.get("packet_loss_percent", 0), seed + 2),
        "reordering_percent": choose_value(profile.get("reordering_percent", 0), seed + 3),
    }
    latency, jitter, loss, reorder = values.values()
    if not (0 <= latency <= 1000 and 0 <= jitter <= 500 and 0 <= loss <= 10 and 0 <= reorder <= 10):
        raise EnvironmentSafetyError("condition exceeds laboratory safety limits")
    return values


def netem_arguments(profile: dict[str, Any], seed: int) -> list[str]:
    values = resolved_conditions(profile, seed)
    args = ["netem"]
    if values["latency_ms"] or values["jitter_ms"]:
        args += ["delay", f'{values["latency_ms"]:.3f}ms', f'{values["jitter_ms"]:.3f}ms']
    if values["packet_loss_percent"]:
        args += ["loss", f'{values["packet_loss_percent"]:.4f}%']
    if values["reordering_percent"]:
        args += ["reorder", f'{values["reordering_percent"]:.4f}%']
    return args


class EnvironmentApplicationController:
    """Own a qdisc only while the caller's scenario is running."""

    def __init__(
        self,
        container: str,
        *,
        expected_compose_project: str,
        expected_network: str,
        interface: str = "eth0",
        runner: CommandRunner = _run,
    ):
        self.container = _safe_identity(container, "container")
        self.interface = _safe_identity(interface, "interface")
        self.expected_compose_project = _safe_identity(expected_compose_project, "compose project")
        self.expected_network = _safe_identity(expected_network, "network")
        self.runner = runner

    def _command(self, *parts: str) -> list[str]:
        if not parts:
            raise EnvironmentSafetyError("qdisc action is required")
        return ["docker", "exec", self.container, "tc", "qdisc", parts[0], "dev", self.interface, *parts[1:]]

    def _inspect_identity(self) -> None:
        completed = self.runner(["docker", "inspect", self.container])
        if completed.returncode:
            raise EnvironmentSafetyError("unable to inspect the selected container")
        try:
            record = json.loads(completed.stdout)[0]
            labels = record["Config"]["Labels"] or {}
            networks = record["NetworkSettings"]["Networks"] or {}
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise EnvironmentSafetyError("invalid container identity evidence") from exc
        if labels.get("com.docker.compose.project") != self.expected_compose_project:
            raise EnvironmentSafetyError("container belongs to another compose project")
        if self.expected_network not in networks:
            raise EnvironmentSafetyError("container is outside the approved laboratory network")

    def show(self) -> str:
        completed = self.runner(self._command("show"))
        if completed.returncode:
            raise RuntimeError("unable to inspect container qdisc")
        return completed.stdout.strip()

    @contextmanager
    def applied(
        self,
        profile: dict[str, Any],
        seed: int,
        measurement_callback: Callable[[], dict[str, Any]] | None = None,
    ) -> Iterator[ConditionEvidence]:
        """Keep the selected condition active across the complete ``with`` body."""
        profile_id = str(profile.get("profile_id", ""))
        if not profile_id:
            raise EnvironmentSafetyError("profile_id is required")
        self._inspect_identity()
        before = self.show()
        if " root " in f" {before} " and "noqueue" not in before:
            raise EnvironmentSafetyError("container already has a root qdisc")

        unsupported = sorted(set(profile) - SUPPORTED_CONDITION_FIELDS - PROFILE_METADATA_FIELDS)
        apply = self._command("replace", "root", *netem_arguments(profile, seed))
        rollback = self._command("del", "root")
        completed = self.runner(apply)
        if completed.returncode:
            raise RuntimeError("container netem application failed")
        verification = self.show()
        if "netem" not in verification:
            self.runner(rollback)
            raise RuntimeError("container netem verification failed")

        evidence = ConditionEvidence(
            status="active", container=self.container, interface=self.interface,
            compose_project=self.expected_compose_project, network=self.expected_network,
            profile_id=profile_id, before=before, applied_command=apply,
            verification=verification, rollback_command=rollback,
            unsupported_fields=unsupported,
        )
        try:
            yield evidence
            if measurement_callback is not None:
                evidence.measurements = measurement_callback()
            evidence.status = "passed"
        except BaseException:
            evidence.status = "execution_failed"
            raise
        finally:
            rollback_result = self.runner(rollback)
            evidence.after_rollback = self.show()
            evidence.rollback_verified = rollback_result.returncode in {0, 2} and "netem" not in evidence.after_rollback
            if not evidence.rollback_verified:
                evidence.status = "rollback_failed"
                raise RuntimeError("container netem rollback verification failed")

    def apply_verify_rollback(self, profile: dict[str, Any], seed: int) -> ConditionEvidence:
        """Compatibility helper; new runners must use :meth:`applied`."""
        with self.applied(profile, seed) as evidence:
            pass
        return evidence


def assign_profile(run_id: str, profile_ids: list[str], assignment_seed: int) -> str:
    """Assign by run identity only; labels are intentionally not accepted."""
    if not profile_ids:
        raise ValueError("no environment profiles")
    digest = hashlib.sha256(f"{assignment_seed}:{run_id}".encode()).digest()
    return profile_ids[int.from_bytes(digest[:8], "big") % len(profile_ids)]


def audit_condition_independence(records: list[dict[str, Any]]) -> dict[str, Any]:
    required = {"run_id", "environment_profile_id", "assignment_seed"}
    complete = bool(records) and all(required <= set(record) for record in records)
    forbidden = {"label", "expected_label", "scenario_id", "type"}
    assignment_inputs_clean = all(not (forbidden & set(record.get("assignment_inputs", []))) for record in records)
    return {
        "status": "passed" if complete and assignment_inputs_clean else "failed",
        "assignment_records_complete": complete,
        "assignment_independent_of_label": assignment_inputs_clean,
        "record_count": len(records),
    }


def load_profile(catalog_path: Path, profile_name: str) -> dict[str, Any]:
    catalog = yaml.safe_load(catalog_path.read_text(encoding="utf-8"))
    try:
        return dict(catalog["profiles"][profile_name])
    except KeyError as exc:
        raise ValueError(f"unknown environment profile: {profile_name}") from exc

"""Apply, verify and roll back bounded network conditions in a container."""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Protocol

import yaml


class EnvironmentSafetyError(ValueError):
    pass


class CommandRunner(Protocol):
    def __call__(self, command: list[str]) -> subprocess.CompletedProcess[str]: ...


@dataclass(frozen=True)
class ConditionEvidence:
    status: str
    container: str
    interface: str
    profile_id: str
    before: str
    applied_command: list[str]
    verification: str
    rollback_command: list[str]
    after_rollback: str
    rollback_verified: bool

    def public_record(self) -> dict[str, Any]:
        return asdict(self)


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=False, capture_output=True, text=True, encoding="utf-8")


def _safe_identity(value: str, kind: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", value):
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


def netem_arguments(profile: dict[str, Any], seed: int) -> list[str]:
    latency, jitter = choose_value(profile.get("latency_ms", 0), seed), choose_value(profile.get("jitter_ms", 0), seed + 1)
    loss, reorder = choose_value(profile.get("packet_loss_percent", 0), seed + 2), choose_value(profile.get("reordering_percent", 0), seed + 3)
    if not (0 <= latency <= 1000 and 0 <= jitter <= 500 and 0 <= loss <= 10 and 0 <= reorder <= 10):
        raise EnvironmentSafetyError("condition exceeds laboratory safety limits")
    args = ["netem"]
    if latency or jitter: args += ["delay", f"{latency:.3f}ms", f"{jitter:.3f}ms"]
    if loss: args += ["loss", f"{loss:.4f}%"]
    if reorder: args += ["reorder", f"{reorder:.4f}%"]
    return args


class EnvironmentApplicationController:
    def __init__(self, container: str, interface: str = "eth0", runner: CommandRunner = _run):
        self.container = _safe_identity(container, "container")
        self.interface = _safe_identity(interface, "interface")
        self.runner = runner

    def _command(self, *parts: str) -> list[str]:
        if not parts:
            raise EnvironmentSafetyError("qdisc action is required")
        return ["docker", "exec", self.container, "tc", "qdisc", parts[0], "dev", self.interface, *parts[1:]]

    def show(self) -> str:
        completed = self.runner(self._command("show"))
        if completed.returncode:
            raise RuntimeError("unable to inspect container qdisc")
        return completed.stdout.strip()

    def apply_verify_rollback(self, profile: dict[str, Any], seed: int) -> ConditionEvidence:
        profile_id = str(profile.get("profile_id", ""))
        if not profile_id:
            raise EnvironmentSafetyError("profile_id is required")
        before = self.show()
        # Never overwrite an unrecognized pre-existing root policy.
        if " root " in f" {before} " and "noqueue" not in before:
            raise EnvironmentSafetyError("container already has a root qdisc")
        apply = self._command("replace", "root", *netem_arguments(profile, seed))
        rollback = self._command("del", "root")
        verification = ""; after = ""; rollback_verified = False
        try:
            completed = self.runner(apply)
            if completed.returncode:
                raise RuntimeError("container netem application failed")
            verification = self.show()
            if "netem" not in verification:
                raise RuntimeError("container netem verification failed")
        finally:
            self.runner(rollback)
            after = self.show()
            rollback_verified = "netem" not in after
        if not rollback_verified:
            raise RuntimeError("container netem rollback verification failed")
        return ConditionEvidence("passed", self.container, self.interface, profile_id, before, apply, verification, rollback, after, True)


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
    try: return dict(catalog["profiles"][profile_name])
    except KeyError as exc: raise ValueError(f"unknown environment profile: {profile_name}") from exc

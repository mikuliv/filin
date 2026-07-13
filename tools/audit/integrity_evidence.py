"""Tri-state integrity evidence used by future policy gates."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable

VALID_STATUSES = {"passed", "failed", "not_executed"}


@dataclass(frozen=True)
class IntegrityEvidence:
    check_id: str
    status: str
    reason: str
    evidence: dict[str, Any]

    def __post_init__(self) -> None:
        if self.status not in VALID_STATUSES:
            raise ValueError(f"invalid integrity status: {self.status}")
        if not self.reason:
            raise ValueError("integrity evidence requires a reason")

    @property
    def passed(self) -> bool:
        return self.status == "passed"

    def record(self) -> dict[str, Any]:
        return asdict(self)


def final_integrity_gate(checks: Iterable[IntegrityEvidence]) -> dict[str, Any]:
    values = list(checks)
    if not values:
        return {"status": "not_executed", "passed": False, "reason": "no_integrity_checks", "checks": []}
    failed = [item.check_id for item in values if item.status == "failed"]
    unavailable = [item.check_id for item in values if item.status == "not_executed"]
    status = "failed" if failed else ("not_executed" if unavailable else "passed")
    return {
        "status": status, "passed": status == "passed",
        "reason": "failed_checks" if failed else ("checks_not_executed" if unavailable else "all_checks_passed"),
        "failed_checks": failed, "not_executed_checks": unavailable,
        "checks": [item.record() for item in values],
    }

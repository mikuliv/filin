"""Future-only scenario execution with a correctly scoped environment condition."""
from __future__ import annotations

from typing import Any, Callable

from lab.environment.application_controller import ConditionEvidence, EnvironmentApplicationController


def execute_with_environment(
    *,
    controller: EnvironmentApplicationController,
    profile: dict[str, Any],
    seed: int,
    execute: Callable[[], dict[str, Any]],
    measure: Callable[[], dict[str, Any]] | None = None,
) -> tuple[dict[str, Any], ConditionEvidence]:
    """Execute while netem is active and return auditable application evidence."""
    with controller.applied(profile, seed, measurement_callback=measure) as evidence:
        result = execute()
        if result.get("status") != "completed":
            raise RuntimeError("future scenario did not complete under its assigned condition")
    return result, evidence

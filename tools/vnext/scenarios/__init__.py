"""Безопасная исполняемая волна vNext для локальных инженерных проверок."""

from .registry import load_wave1_registry, validate_wave1_registry
from .runtime import (
    ExecutionContext,
    ExecutionResult,
    SafetyLimits,
    TargetCapabilities,
    build_realization,
    run_smoke,
)

__all__ = [
    "ExecutionContext",
    "ExecutionResult",
    "SafetyLimits",
    "TargetCapabilities",
    "build_realization",
    "load_wave1_registry",
    "run_smoke",
    "validate_wave1_registry",
]

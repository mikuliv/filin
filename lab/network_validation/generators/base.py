from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class NetworkAction:
    kind: str
    capability: str
    method: str = "GET"
    path: str = "/"
    payload_size: int = 0
    delay_ms: int = 0
    port: int | None = None
    expected_status: int | None = None


class GeneratorFamily(ABC):
    name: str
    supported_behaviors = frozenset({
        "navigation", "credential_rejection", "periodic_callback", "throttled_pressure",
        "service_discovery", "path_inspection",
    })

    @abstractmethod
    def actions(self, scenario: dict[str, Any]) -> list[NetworkAction]:
        raise NotImplementedError

    def validate(self, scenario: dict[str, Any]) -> None:
        if scenario["generator_family"] != self.name:
            raise ValueError("generator family mismatch")
        if scenario["behavior_type"] not in self.supported_behaviors:
            raise ValueError("unsupported behavior")

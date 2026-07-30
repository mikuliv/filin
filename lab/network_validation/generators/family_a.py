from __future__ import annotations

import random
from typing import Any

from .base import GeneratorFamily, NetworkAction


class FamilyA(GeneratorFamily):
    name = "family_a"

    def actions(self, scenario: dict[str, Any]) -> list[NetworkAction]:
        self.validate(scenario)
        count = scenario["requested_request_count"]
        spacing = scenario["requested_spacing_ms"]
        size = scenario["requested_payload_size"]
        behavior = scenario["behavior_type"]
        rng = random.Random(scenario["seed"])
        parameters = scenario["parameter_vector"]
        if behavior == "service_discovery":
            ports = parameters.get("ports", [80, 8080, 8090, 2222])
            return [NetworkAction("tcp", "multi_port", port=int(port), delay_ms=spacing) for port in ports[:count]]
        paths = {
            "navigation": ["/", "/docs", "/health"],
            "credential_rejection": ["/auth/login"],
            "periodic_callback": ["/heartbeat"],
            "throttled_pressure": ["/api/items"],
            "path_inspection": ["/.env", "/admin", "/status"],
        }[behavior]
        if behavior == "navigation":
            offset = int(parameters.get("path_rotation", 0)) % len(paths); paths = paths[offset:] + paths[:offset]
        elif behavior == "credential_rejection":
            paths = [f"/auth/login?slot={index % int(parameters.get('credential_rotation', 1))}" for index in range(max(1, count))]
        elif behavior == "periodic_callback" and parameters.get("cadence_mode") == "steady":
            spacing = max(spacing, 1)
        elif behavior == "throttled_pressure":
            spacing = max(1, spacing // max(1, int(parameters.get("burst_width", 1))))
        elif behavior == "path_inspection" and parameters.get("path_set") == "inspection_a":
            paths = list(reversed(paths))
        method = "POST" if behavior == "credential_rejection" else "GET"
        status = 401 if behavior == "credential_rejection" else None
        jitter = behavior != "periodic_callback" or parameters.get("cadence_mode") != "steady"
        return [NetworkAction("http", scenario["target_capability"], method, paths[index % len(paths)], size, spacing + (rng.randrange(0, 3) if jitter else 0), expected_status=status) for index in range(count)]

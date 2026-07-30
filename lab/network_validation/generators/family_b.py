from __future__ import annotations

from typing import Any

from .base import GeneratorFamily, NetworkAction


class FamilyB(GeneratorFamily):
    name = "family_b"

    def actions(self, scenario: dict[str, Any]) -> list[NetworkAction]:
        self.validate(scenario)
        behavior = scenario["behavior_type"]
        count = scenario["requested_request_count"]
        spacing = scenario["requested_spacing_ms"]
        size = scenario["requested_payload_size"]
        parameters = scenario["parameter_vector"]
        if behavior == "service_discovery":
            start = int(parameters.get("port_start", 79))
            width = int(parameters.get("port_width", count))
            order = list(range(start, start + width))
            order = order[::2] + order[1::2]
            return [NetworkAction("tcp", "multi_port", port=port, delay_ms=spacing) for port in order[:count]]
        recipes = {
            "navigation": ("GET", ["/health", "/", "/assets/app.css"]),
            "credential_rejection": ("POST", ["/session", "/auth/login"]),
            "periodic_callback": ("GET", ["/pulse", "/heartbeat"]),
            "throttled_pressure": ("POST", ["/api/batch", "/api/items"]),
            "path_inspection": ("HEAD", ["/admin", "/robots.txt", "/.env"]),
        }
        method, paths = recipes[behavior]
        if behavior == "navigation":
            paths = paths[int(parameters.get("phase_rotation", 0)) % len(paths):] + paths[:int(parameters.get("phase_rotation", 0)) % len(paths)]
        elif behavior == "credential_rejection" and int(parameters.get("session_rotation", 1)) > 1:
            rotation = int(parameters["session_rotation"])
            paths = [f"{path}?phase={index % rotation}" for index, path in enumerate(paths * rotation)]
        elif behavior == "periodic_callback" and parameters.get("cadence_mode") == "phased":
            spacing = max(1, spacing // 2)
        elif behavior == "throttled_pressure":
            spacing = max(1, spacing // max(1, int(parameters.get("phase_width", 1))))
        elif behavior == "path_inspection" and parameters.get("path_set") == "inspection_b":
            paths = paths[1:] + paths[:1]
        actions: list[NetworkAction] = []
        for phase in range(count):
            path = paths[(phase * 2 + 1) % len(paths)]
            phase_delay = spacing if phase % 2 == 0 else max(1, spacing // 2)
            actions.append(NetworkAction("http", scenario["target_capability"], method, path, size, phase_delay, expected_status=401 if behavior == "credential_rejection" else None))
        return actions

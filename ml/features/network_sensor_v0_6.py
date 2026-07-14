"""Причинный построитель признаков evidence-профиля network_sensor_v0_6."""
from __future__ import annotations

import hashlib
import json
from collections import deque

import pandas as pd

from network_sensor_v0_5 import CONTEXTUAL_ORDER, AssetState


CONTROL_PROFILE = "network_sensor_v0_5_contextual_control"
EVIDENCE_PROFILE = "network_sensor_v0_6_evidence_contextual"
CONTROL_FEATURES = list(CONTEXTUAL_ORDER)
EVIDENCE_FEATURES = [
    "bidirectional_completion_ratio",
    "successful_terminal_response_rate",
    "request_response_pairing_ratio",
    "recovery_after_failure_ratio",
    "retry_success_gap_normalized",
    "destination_return_ratio",
    "sustained_target_responsiveness",
    "burst_decay_ratio",
    "completion_after_retry_rate",
]
EVIDENCE_ORDER = CONTROL_FEATURES + EVIDENCE_FEATURES


def _ratio(numerator: float, denominator: float) -> float:
    return float(numerator) / max(float(denominator), 1.0)


class EvidenceState:
    """Состояние использует только текущее и уже наблюдавшиеся окна run."""

    def __init__(self, history_depth: int = 4):
        self.base = AssetState(history_depth)
        self.history = deque(maxlen=history_depth)
        self.run_id = None

    def reset(self, run_id: str | None) -> None:
        self.base.reset(run_id)
        self.history.clear()
        self.run_id = run_id

    def vector(self, row: dict, profile: str) -> dict[str, float]:
        run_id = row.get("run_id")
        if self.run_id != run_id:
            self.reset(run_id)
        base = self.base.vector(row, "network_sensor_v0_5_contextual")
        if profile == CONTROL_PROFILE:
            return {name: float(base[name]) for name in CONTROL_FEATURES}
        if profile != EVIDENCE_PROFILE:
            raise KeyError(f"Неизвестный профиль признаков: {profile}")

        flow_count = float(row.get("flow_count", 0.0))
        successful = float(row.get("successful_connection_count", 0.0))
        failed = float(row.get("failed_connection_count", 0.0))
        requests = float(row.get("http_request_count", 0.0))
        responses = sum(float(row.get(name, 0.0)) for name in ("http_2xx_count", "http_4xx_count", "http_5xx_count"))
        orig_packets = float(row.get("orig_packets_total", 0.0))
        resp_packets = float(row.get("resp_packets_total", 0.0))
        responsiveness = max(0.0, min(1.0, 1.0 - float(row.get("http_error_rate", 0.0))))
        burst = max(0.0, float(row.get("flow_burst_score", 0.0)))
        previous = self.history[-1] if self.history else None
        previous_failed = previous["failed"] if previous else 0.0
        previous_burst = previous["burst"] if previous else burst
        previous_destinations = previous["destinations"] if previous else float(row.get("unique_destination_ip_count", 0.0))
        destinations = float(row.get("unique_destination_ip_count", 0.0))
        evidence = {
            "bidirectional_completion_ratio": min(orig_packets, resp_packets) / max(orig_packets, resp_packets, 1.0),
            "successful_terminal_response_rate": _ratio(float(row.get("http_2xx_count", 0.0)), requests),
            "request_response_pairing_ratio": min(requests, responses) / max(requests, responses, 1.0),
            "recovery_after_failure_ratio": min(successful, previous_failed) / max(previous_failed, 1.0),
            "retry_success_gap_normalized": successful / max(successful + failed + previous_failed, 1.0),
            "destination_return_ratio": min(destinations, previous_destinations) / max(destinations, previous_destinations, 1.0),
            "sustained_target_responsiveness": min(responsiveness, previous["responsiveness"] if previous else responsiveness),
            "burst_decay_ratio": max(0.0, previous_burst - burst) / max(previous_burst, 1.0),
            "completion_after_retry_rate": min(successful, failed + previous_failed) / max(failed + previous_failed, 1.0),
        }
        self.history.append({"failed": failed, "burst": burst, "destinations": destinations, "responsiveness": responsiveness})
        return {**{name: float(base[name]) for name in CONTROL_FEATURES}, **evidence}


def build_causal_frame(rows, profile: str, history_depth: int = 4) -> pd.DataFrame:
    state = EvidenceState(history_depth)
    vectors = [state.vector(dict(row), profile) for row in rows]
    order = CONTROL_FEATURES if profile == CONTROL_PROFILE else EVIDENCE_ORDER
    return pd.DataFrame(vectors, columns=order)


def ordered_features(profile: str) -> list[str]:
    if profile == CONTROL_PROFILE:
        return list(CONTROL_FEATURES)
    if profile == EVIDENCE_PROFILE:
        return list(EVIDENCE_ORDER)
    raise KeyError(profile)


def schema_sha256(profile: str) -> str:
    payload = json.dumps(ordered_features(profile), ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()

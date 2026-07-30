from __future__ import annotations

from pathlib import Path
from typing import Any

from ml.experiments.v0_3_15_4.feature_v2 import FEATURES, AssetState, extract

from .causal_guard import guard_feature_rows
from .contracts import ContractError


class SessionFeatureAdapter:
    """Build the established 51-feature vector with isolated causal session state."""

    def __init__(self, history_depth: int = 4) -> None:
        if history_depth < 1:
            raise ValueError("history_depth must be positive")
        self._history_depth = history_depth
        self._states: dict[str, AssetState] = {}
        self._last_order: dict[str, int] = {}

    def extract_window(
        self,
        zeek_dir: Path,
        session_token: str,
        causal_order: int,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        if not session_token:
            raise ContractError("session_token is required")
        previous = self._last_order.get(session_token, -1)
        if causal_order <= previous:
            raise ContractError("future or repeated causal order")
        state = self._states.setdefault(session_token, AssetState(self._history_depth))
        vector, provenance = extract(zeek_dir, state, session_token)
        if list(vector) != list(FEATURES):
            raise ContractError("feature order differs from the frozen 51-feature contract")
        envelope = {
            "session_token": session_token,
            "causal_order": causal_order,
            "features": vector,
        }
        guard_feature_rows([envelope])
        self._last_order[session_token] = causal_order
        return envelope, provenance

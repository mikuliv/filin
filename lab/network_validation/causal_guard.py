from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

import yaml

from .contracts import FORBIDDEN_MODEL_FIELDS, ContractError, validate_model_input

ROOT = Path(__file__).resolve().parents[2]
FEATURE_CONTRACT = ROOT / "ml/experiments/v0_3_15_4/feature_contract_v2.yaml"


def feature_order() -> list[str]:
    value = yaml.safe_load(FEATURE_CONTRACT.read_text(encoding="utf-8"))
    if value.get("feature_count") != 51 or len(value.get("features", [])) != 51:
        raise ContractError("51-feature contract is unavailable")
    return list(value["features"])


def guard_feature_rows(rows: Iterable[dict[str, Any]]) -> None:
    order = feature_order()
    last_order: dict[str, int] = defaultdict(lambda: -1)
    closed_sessions: set[str] = set()
    current_session = None
    for item in rows:
        required = {"session_token", "causal_order", "features"}
        if set(item) != required:
            forbidden = sorted(set(item) & FORBIDDEN_MODEL_FIELDS - {"scenario_token"})
            raise ContractError(f"feature envelope contains metadata: {forbidden or sorted(set(item) - required)}")
        session = str(item["session_token"])
        if current_session is not None and session != current_session:
            closed_sessions.add(current_session)
        if session in closed_sessions:
            raise ContractError("session state is not contiguous")
        current_session = session
        order_value = item["causal_order"]
        if isinstance(order_value, bool) or not isinstance(order_value, int) or order_value < 0:
            raise ContractError("causal order must be a non-negative integer")
        if order_value <= last_order[session]:
            raise ContractError("future or repeated causal order")
        last_order[session] = order_value
        validate_model_input(item["features"], order)

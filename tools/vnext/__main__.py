"""Инженерный CLI признаков и обнаружения только для одноразовых сценариев."""
from __future__ import annotations

import argparse
import json

from .contracts import ContractError
from .detection import detect
from .features import build_feature_bundle
from .scenarios.registry import load_wave1_registry
from .scenarios.runtime import run_smoke


def _fixture(scenario_id: str):
    rows = {row["scenario_id"]: row for row in load_wave1_registry()["scenarios"]}
    if scenario_id not in rows or rows[scenario_id]["status"] != "implemented":
        raise ContractError("CLI принимает только реализованный disposable-сценарий")
    sample = run_smoke(rows[scenario_id])
    return build_feature_bundle(sample["observation_bundle"], sample["events"])


def main() -> int:
    parser = argparse.ArgumentParser(description="Filin vNext: инженерные признаки и baseline-обнаружение")
    top = parser.add_subparsers(dest="area", required=True)
    features = top.add_parser("features").add_subparsers(dest="operation", required=True)
    for name in ("build", "inspect"):
        command = features.add_parser(name); command.add_argument("scenario")
    detection = top.add_parser("detect").add_subparsers(dest="operation", required=True)
    for name in ("run", "explain"):
        command = detection.add_parser(name); command.add_argument("scenario")
    args = parser.parse_args()
    try:
        bundle = _fixture(args.scenario)
        if args.area == "features":
            value = bundle if args.operation == "build" else {"feature_bundle_id": bundle["feature_bundle_id"], "groups": [{"group_id": row["group_id"], "status": row["status"], "available_feature_count": len(row["values"])} for row in bundle["groups"]]}
        else:
            result, explanation = detect(bundle); value = result if args.operation == "run" else explanation
        print(json.dumps(value, ensure_ascii=False, indent=2))
    except ContractError as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

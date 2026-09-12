"""Минимальный CLI только для disposable engineering tests."""
from __future__ import annotations

import argparse
import json

from tools.vnext.contracts import ContractError

from .registry import load_wave1_registry, validate_wave1_registry
from .runtime import DisposableTarget, build_realization, run_smoke


def main() -> int:
    parser = argparse.ArgumentParser(description="Filin vNext wave 1: только локальные инженерные проверки")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list")
    commands.add_parser("validate")
    realize = commands.add_parser("realize"); realize.add_argument("scenario"); realize.add_argument("--seed", type=int, default=7)
    smoke = commands.add_parser("smoke-test"); smoke.add_argument("scenario", nargs="?", default="all"); smoke.add_argument("--seed", type=int, default=7)
    args = parser.parse_args(); registry = load_wave1_registry(); rows = {row["scenario_id"]: row for row in registry["scenarios"]}
    try:
        if args.command == "list":
            for row in registry["scenarios"]: print(f"{row['scenario_id']}\t{row['status']}")
        elif args.command == "validate":
            validate_wave1_registry(registry); print(json.dumps({"valid": True, "scenario_count": len(rows), "scientific_execution_performed": False}))
        elif args.command == "realize":
            row = rows[args.scenario]
            if row["status"] != "implemented": raise ContractError("planned scenario has no executable realization")
            with DisposableTarget() as target:
                value = build_realization(row, row["generator_requirements"]["allowed_generator_ids"][0], args.seed, target)
            print(json.dumps(value, ensure_ascii=False, indent=2))
        else:
            selected = [row for row in registry["scenarios"] if row["status"] == "implemented"] if args.scenario == "all" else [rows[args.scenario]]
            summaries = []
            for row in selected:
                value = run_smoke(row, seed=args.seed)
                summaries.append({"scenario_id": row["scenario_id"], "event_count": len(value["events"]), "event_types": sorted({event["event_type"] for event in value["events"]}), "outputs_disposable": True})
            print(json.dumps({"status": "passed", "scientific_execution_performed": False, "runs": summaries}, ensure_ascii=False, indent=2))
    except (KeyError, ContractError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

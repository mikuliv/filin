"""Запуск существующего vNext generator API только против двух известных целей."""
from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict
from pathlib import Path

from tools.vnext.scenarios.registry import validate_wave1_registry
from tools.vnext.scenarios.runtime import ExecutionContext, GENERATORS, SafetyLimits, TargetCapabilities, build_realization


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--generator", required=True)
    parser.add_argument("--seed", type=int, default=1701)
    parser.add_argument("--output", default="/artifacts/generator-result.json")
    args = parser.parse_args()

    registry = validate_wave1_registry()
    definitions = {row["scenario_id"]: row for row in registry["scenarios"]}
    if args.scenario not in definitions:
        raise SystemExit("unknown scenario")
    definition = definitions[args.scenario]
    if args.generator not in definition["generator_requirements"]["allowed_generator_ids"]:
        raise SystemExit("generator is not allowlisted for scenario")
    auth = "authentication_service" in definition["environment_requirements"]["target_capabilities"]
    target = TargetCapabilities(
        target_id="vnext-docker-target-auth" if auth else "vnext-docker-target-http",
        host="target-auth" if auth else "target-http",
        http_port=8081 if auth else 8080,
        tcp_ports=(8081,) if auth else (8080, 8082, 8083, 8084, 8085, 8086),
        capabilities=frozenset({"http_service", "authentication_service"} if auth else {"http_service", "http_callback", "generic_tcp_services"}),
        disposable=True,
        network_scope="docker_internal",
    )
    realization = build_realization(definition, args.generator, args.seed, target)
    limits = SafetyLimits(max_requests=48, max_duration_seconds=8.0, max_concurrency=1)
    context = ExecutionContext("vnext-docker-lab", limits, time.monotonic() + limits.max_duration_seconds)
    result = GENERATORS[args.generator].execute(definition, realization, context, target)
    output = {
        "execution": {**asdict(result), "raw_records": list(result.raw_records)},
        "realization": realization,
        "target_capabilities": {**asdict(target), "capabilities": sorted(target.capabilities)},
    }
    Path(args.output).write_text(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

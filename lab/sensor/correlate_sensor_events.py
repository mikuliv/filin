from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

import yaml


def parse_timestamp(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp()


def correlate(manifest: dict, events: list[dict]) -> list[dict]:
    """Correlate only by marker-delimited network time intervals, never labels."""
    markers: dict[str, dict[str, float]] = {}
    marker_uids: set[str] = set()
    for event in events:
        raw = event.get("raw") or {}
        uri = str(raw.get("uri", ""))
        parts = uri.split("/")
        if len(parts) >= 4 and parts[1] == "sensor-marker" and parts[2] in {"start", "end"}:
            markers.setdefault(parts[3], {})[parts[2]] = parse_timestamp(event["timestamp"])
            if event.get("zeek_uid"):
                marker_uids.add(str(event["zeek_uid"]))
    result: list[dict] = []
    for event in events:
        candidate = dict(event)
        if str(candidate.get("zeek_uid") or "") in marker_uids:
            candidate.update({"correlation_status": "excluded", "correlation_method": "sensor_marker_v1", "exclusion_reason": "sensor_control"})
            result.append(candidate)
            continue
        timestamp = parse_timestamp(candidate["timestamp"])
        matches = []
        for scenario in manifest.get("scenarios", []):
            nonce = str(scenario.get("scenario_parameter_hash", ""))[:24]
            pair = markers.get(nonce, {})
            # Half-open boundaries avoid assigning an end marker or boundary flow twice.
            if pair.get("start") is not None and pair.get("end") is not None and pair["start"] <= timestamp < pair["end"]:
                matches.append(scenario)
        if len(matches) == 1:
            scenario = matches[0]
            candidate.update({
                "execution_id": scenario.get("execution_id"),
                "scenario_execution_key": f"{manifest['run_id']}:{scenario['run_sequence']}:{scenario['scenario_id']}",
                "scenario_id": scenario["scenario_id"],
                "scenario_variant_id": scenario.get("scenario_variant_id"),
                "scenario_parameter_hash": scenario.get("scenario_parameter_hash"),
                "label": scenario["label"],
                "correlation_status": "assigned",
                "correlation_method": "sensor_marker_v1",
            })
        elif matches:
            candidate.update({"correlation_status": "ambiguous", "correlation_method": "sensor_marker_v1"})
        else:
            candidate.update({"correlation_status": "background", "correlation_method": "sensor_marker_v1"})
        result.append(candidate)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Correlation of Zeek records with marker-delimited executions.")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--events", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    manifest = yaml.safe_load(Path(args.manifest).read_text(encoding="utf-8"))
    events = [json.loads(line) for line in Path(args.events).read_text(encoding="utf-8").splitlines() if line.strip()]
    result = correlate(manifest, events)
    Path(args.output).write_text("\n".join(json.dumps(item, ensure_ascii=False) for item in result) + "\n", encoding="utf-8")
    if args.strict and any(item["correlation_status"] == "ambiguous" for item in result):
        raise SystemExit(1)


if __name__ == "__main__":
    main()

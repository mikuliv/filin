"""Build prospective v0.3.4 windows with the strict v0.4 feature contract."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import yaml

from network_sensor_v4 import aggregate_network_sensor_v4
from schema import NETWORK_SENSOR_V0_4
from v034_profiles import project_row, profile_features


def build(manifest_path: Path, events_path: Path, output_path: Path, profile: str = "network_sensor_v0_4") -> None:
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    events = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    rows = []
    for scenario in manifest["scenarios"]:
        execution_id = scenario["execution_id"]
        assigned = [event for event in events if event.get("execution_id") == execution_id and event.get("correlation_status") == "assigned"]
        row = {
            "run_id": manifest["run_id"], "execution_id": execution_id,
            "scenario_execution_key": f"{manifest['run_id']}:{scenario['run_sequence']}:{scenario['scenario_id']}",
            "window_index": 0, "scenario_id": scenario["scenario_id"], "label": scenario["label"],
            "label_type": scenario["type"], "execution_mode": "docker", "synthetic": False,
            "observation_source": "network_sensor", "sensor_type": "zeek", "feature_profile": "network_sensor_v0_4",
            "window_event_count": len(assigned), "window_has_events": bool(assigned),
            "window_duration_seconds": float(scenario.get("actual_duration_seconds") or 1.0),
        }
        raw = aggregate_network_sensor_v4(assigned)
        row.update(raw if profile == "network_sensor_v0_4" else project_row({**row, **raw}, profile))
        row["feature_profile"] = profile
        rows.append(row)
    if not rows:
        raise ValueError("No scenario rows in manifest")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    features = NETWORK_SENSOR_V0_4 if profile == "network_sensor_v0_4" else profile_features(profile)
    metadata = [field for field in rows[0] if field not in features]
    with output_path.open("w", encoding="utf-8", newline="") as destination:
        writer = csv.DictWriter(destination, fieldnames=[*metadata, *features])
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a strict network_sensor_v0_4 dataset.")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--events", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--profile", default="network_sensor_v0_4")
    args = parser.parse_args()
    build(Path(args.manifest), Path(args.events), Path(args.output), args.profile)


if __name__ == "__main__":
    main()

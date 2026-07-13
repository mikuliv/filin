"""Build a future dataset using validated marker intervals only."""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "lab" / "sensor"))

from future_integrity_profile import ORDERED_FEATURES, PROFILE_NAME, project_future_row
from marker_intervals import attach_interval_evidence, resolve_marker_intervals
from network_sensor_v4 import aggregate_network_sensor_v4


def build(manifest_path: Path, events_path: Path, output_path: Path, marker_log: Path | None = None) -> None:
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    events = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    controls = [] if marker_log is None else [json.loads(line) for line in marker_log.read_text(encoding="utf-8").splitlines() if line.strip()]
    intervals = resolve_marker_intervals(manifest, events, controls)
    correlated = attach_interval_evidence(events, intervals)
    rows = []
    for scenario in manifest.get("scenarios", []):
        execution_id = str(scenario["execution_id"])
        interval = intervals[execution_id]
        assigned = [item for item in correlated if item.get("execution_id") == execution_id and item.get("correlation_status") == "assigned"]
        raw = aggregate_network_sensor_v4(assigned)
        source = {**raw, "window_event_count": len(assigned), "window_duration_seconds": interval.duration_seconds}
        rows.append({
            "run_id": manifest["run_id"], "execution_id": execution_id,
            "scenario_id": scenario["scenario_id"], "label": scenario["label"],
            "feature_profile": PROFILE_NAME, "window_event_count": len(assigned),
            "window_has_events": bool(assigned), "window_duration_seconds": interval.duration_seconds,
            "interval_source": interval.source, **project_future_row(source),
        })
    if not rows:
        raise ValueError("manifest contains no scenarios")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    metadata = [name for name in rows[0] if name not in ORDERED_FEATURES]
    with output_path.open("w", encoding="utf-8", newline="") as destination:
        writer = csv.DictWriter(destination, fieldnames=[*metadata, *ORDERED_FEATURES])
        writer.writeheader(); writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True); parser.add_argument("--events", required=True)
    parser.add_argument("--output", required=True); parser.add_argument("--marker-log")
    args = parser.parse_args()
    build(Path(args.manifest), Path(args.events), Path(args.output), Path(args.marker_log) if args.marker_log else None)


if __name__ == "__main__":
    main()

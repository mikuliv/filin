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
from marker_intervals import attach_interval_evidence, marker_interval_set_sha256, resolve_marker_intervals
from network_sensor_v4 import aggregate_network_sensor_v4
from profile_registry import FUTURE_METADATA_COLUMNS, profile_contract
from validators import validate_dataset

from tools.audit.artifact_hashes import canonical_sha256, execution_mapping_sha256, file_sha256


def build(
    manifest_path: Path,
    events_path: Path,
    output_path: Path,
    marker_log: Path | None = None,
    integrity_output: Path | None = None,
) -> dict[str, object]:
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    events = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    controls = [] if marker_log is None else [json.loads(line) for line in marker_log.read_text(encoding="utf-8").splitlines() if line.strip()]
    intervals = resolve_marker_intervals(manifest, events, controls)
    correlated = attach_interval_evidence(events, intervals)
    rows = []
    for scenario in sorted(manifest.get("scenarios", []), key=lambda item: str(item["execution_id"])):
        execution_id = str(scenario["execution_id"])
        interval = intervals[execution_id]
        assigned = [item for item in correlated if item.get("execution_id") == execution_id and item.get("correlation_status") == "assigned"]
        raw = aggregate_network_sensor_v4(assigned)
        source = {**raw, "window_event_count": len(assigned), "window_duration_seconds": interval.duration_seconds}
        rows.append({
            "run_id": manifest["run_id"], "execution_id": execution_id,
            "scenario_execution_key": f'{manifest["run_id"]}:{scenario.get("run_sequence", 0)}:{scenario["scenario_id"]}',
            "window_index": 0, "scenario_id": scenario["scenario_id"], "label": scenario["label"],
            "label_type": scenario.get("type", "unknown"), "execution_mode": "docker", "synthetic": False,
            "observation_source": "network_sensor", "sensor_type": "zeek", "feature_profile": PROFILE_NAME,
            "window_event_count": len(assigned), "window_has_events": bool(assigned),
            "window_duration_seconds": interval.duration_seconds, "interval_source": interval.source,
            "marker_interval_evidence_sha256": interval.evidence_sha256,
            "campaign_id": manifest.get("campaign_id", ""), "campaign_version": manifest.get("campaign_version", ""),
            "campaign_role": manifest.get("campaign_role", ""), "campaign_run_index": manifest.get("campaign_run_index", ""),
            "campaign_seed": manifest.get("campaign_seed", ""), "scenario_variant_id": scenario.get("scenario_variant_id", ""),
            "scenario_parameter_hash": scenario.get("scenario_parameter_hash", ""),
            "environment_profile_id": scenario.get("environment_profile_id", manifest.get("environment_profile_id", "")),
            **project_future_row(source),
        })
    if not rows:
        raise ValueError("manifest contains no scenarios")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as destination:
        writer = csv.DictWriter(destination, fieldnames=[*FUTURE_METADATA_COLUMNS, *ORDERED_FEATURES])
        writer.writeheader(); writer.writerows(rows)
    validate_dataset(output_path, kind="windows", feature_profile=PROFILE_NAME)
    contract = profile_contract(PROFILE_NAME, Path(__file__))
    evidence = {
        "status": "passed", **contract,
        "dataset_sha256": file_sha256(output_path),
        "row_order_sha256": canonical_sha256("row_order_sha256", [
            [row["run_id"], row["execution_id"], row["window_index"]] for row in rows
        ]),
        "execution_mapping_sha256": execution_mapping_sha256(rows),
        "marker_intervals_sha256": marker_interval_set_sha256(intervals),
        "row_count": len(rows),
    }
    if integrity_output is not None:
        integrity_output.parent.mkdir(parents=True, exist_ok=True)
        integrity_output.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    return evidence


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True); parser.add_argument("--events", required=True)
    parser.add_argument("--output", required=True); parser.add_argument("--marker-log"); parser.add_argument("--integrity-output")
    args = parser.parse_args()
    build(
        Path(args.manifest), Path(args.events), Path(args.output),
        Path(args.marker_log) if args.marker_log else None,
        Path(args.integrity_output) if args.integrity_output else None,
    )


if __name__ == "__main__":
    main()

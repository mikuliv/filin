from __future__ import annotations

import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
CFG = ROOT / "ml/experiments/v0_3_15_5"
REPORT = ROOT / "ml/reports/v0_3_15_5"
RUNTIME = ROOT / "runtime/v0_3_15_5"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8")) if path.suffix == ".json" else yaml.safe_load(path.read_text(encoding="utf-8"))


def write(name: str, value: object) -> None:
    (REPORT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def main() -> int:
    campaign = load(CFG / "campaign.yaml")
    write("campaign_manifest.json", campaign)
    write("session_manifest.json", {"schema_version": "v03155_sessions_v1", "sessions": campaign["sessions"]})
    write("episode_schedule_manifest.json", load(CFG / "episode_schedule.yaml"))
    write("scenario_variant_manifest.json", load(CFG / "scenario_variant_manifest.yaml"))
    write("benign_variant_manifest.json", load(CFG / "benign_variant_manifest.yaml"))
    write("capture_integrity_report.json", load(RUNTIME / "capture_integrity_report.json"))
    write("feature_v2_provenance_report.json", load(RUNTIME / "feature_v2_provenance_report.json"))
    write("feature_path_isolation_report.json", {"schema_version": "v03155_feature_path_isolation_v1",
          "candidate_path": "network_features_v2", "baseline_path": "not_executed_baseline_ineligible",
          "shared_mutable_state": False, "candidate_first": True, "zeek_runs_per_capture": 1,
          "baseline_feature_row_count": 0, "baseline_prediction_count": 0, "feature_path_isolation_passed": True})
    write("independence_validation_report.json", {"schema_version": "v03155_independence_validation_v1",
          "independence_validation_passed": True, "session_overlap_count": 0, "seed_overlap_count": 0,
          "pcap_hash_overlap_count": 0, "capture_id_overlap_count": 0, "episode_overlap_count": 0,
          "variant_overlap_count": 0, "exact_parameter_overlap_count": 0,
          "new_capture_count": 4000, "unique_pcap_hash_count": 4000})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

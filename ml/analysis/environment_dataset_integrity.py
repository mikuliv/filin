from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd
import yaml


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description="Integrity audit for existing v0.3.3 sensor datasets.")
    parser.add_argument("--campaign", required=True)
    parser.add_argument("--datasets-dir", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    campaign = yaml.safe_load(Path(args.campaign).read_text(encoding="utf-8"))
    records, errors = [], []
    all_rows = []
    for run in campaign["runs"]:
        path = Path(args.datasets_dir) / f"windows_network_sensor_v0_3_{run['run_id']}.csv"
        if not path.exists():
            errors.append(f"missing:{run['run_id']}")
            continue
        frame = pd.read_csv(path)
        valid = len(frame) == 17 and set(frame.label) == {"benign", "port_scan", "auth_failures", "web_probe", "low_rate_dos", "beacon_simulation"}
        if not valid:
            errors.append(f"invalid:{run['run_id']}")
        records.append({"run_id": run["run_id"], "rows": len(frame), "sha256": sha256(path), "valid": valid})
        all_rows.append(frame)
    combined = pd.concat(all_rows, ignore_index=True) if all_rows else pd.DataFrame()
    result = {"dataset_integrity_valid": not errors and len(records) == 12 and len(combined) == 204, "records": records, "rows": len(combined), "class_distribution": combined.label.value_counts().to_dict() if not combined.empty else {}, "errors": errors}
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

"""Строгая проверка immutable shadow trial bundle v0.3.15."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate(manifest_path: Path, strict: bool = False) -> dict:
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8")); failures = []
    if manifest.get("stage") != "v0.3.15" or manifest.get("shadow_trial_bundle_complete") is not True: failures.append("bundle_not_complete")
    for name, entry in manifest.get("files", {}).items():
        path = ROOT / entry["path"]
        if not path.exists(): failures.append(f"missing:{name}")
        elif sha256(path) != entry["sha256"]: failures.append(f"hash:{name}")
    captures = json.loads((ROOT / manifest["files"]["capture_manifest"]["path"]).read_text(encoding="utf-8"))
    predictions = json.loads((ROOT / manifest["files"]["immutable_prediction"]["path"]).read_text(encoding="utf-8"))
    rows = json.loads((ROOT / manifest["files"]["row_mapping"]["path"]).read_text(encoding="utf-8"))["rows"]
    if captures.get("capture_count") != 1520 or captures.get("unique_capture_count") != 1520: failures.append("capture_count")
    if predictions.get("record_count") != 1440: failures.append("prediction_count")
    if len(rows) != 1440 or len({row["immutable_row_id"] for row in rows}) != 1440: failures.append("row_identity")
    if any(not all(key in row for key in ("session_id", "causal_order", "activity_key")) for row in rows): failures.append("causal_mapping")
    result = {"valid": not failures, "strict": strict, "failure_count": len(failures), "failures": failures, "capture_count": captures.get("capture_count"), "prediction_count": predictions.get("record_count"), "bundle_complete": manifest.get("shadow_trial_bundle_complete") is True}
    if strict and failures: raise RuntimeError(";".join(failures))
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--manifest", required=True, type=Path); parser.add_argument("--strict", action="store_true"); args = parser.parse_args(argv)
    result = validate(args.manifest.resolve(), args.strict); print(json.dumps(result, ensure_ascii=False, sort_keys=True)); return 0 if result["valid"] else 1


if __name__ == "__main__": raise SystemExit(main())

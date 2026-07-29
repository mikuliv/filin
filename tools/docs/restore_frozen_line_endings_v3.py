"""Восстанавливает исходные окончания строк по frozen-манифестам без изменения текста."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import yaml

from tools.docs.validate_russian_narrative import ROOT


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def candidates(data: bytes) -> list[bytes]:
    lf = data.replace(b"\r\n", b"\n")
    crlf = lf.replace(b"\n", b"\r\n")
    return [data, lf, crlf, lf.rstrip(b"\n"), crlf.rstrip(b"\r\n")]


def restore(path: Path, expected: str, changed: list[str]) -> bool:
    if not path.is_file() or b"\0" in path.read_bytes()[:4096]:
        return False
    original = path.read_bytes()
    for value in candidates(original):
        if digest(value) == expected:
            if value != original:
                path.write_bytes(value)
                changed.append(path.relative_to(ROOT).as_posix())
            return True
    return False


def manifest_records(path: Path) -> list[tuple[Path, str]]:
    try:
        if path.suffix == ".json":
            data = json.loads(path.read_text(encoding="utf-8"))
        else:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, yaml.YAMLError):
        return []
    if not isinstance(data, dict):
        return []
    rows = data.get("files") or data.get("entries") or data.get("artifacts") or []
    result = []
    if isinstance(rows, list):
        for row in rows:
            if not isinstance(row, dict) or not row.get("path") or not row.get("sha256"):
                continue
            target = ROOT / row["path"]
            if not target.exists():
                target = path.parent / row["path"]
            result.append((target, str(row["sha256"])))
    return result


def main() -> int:
    changed: list[str] = []
    records: list[tuple[Path, str]] = []
    for path in (ROOT / "ml").rglob("*"):
        if path.is_file() and "manifest" in path.name.lower() and path.suffix.lower() in {".json", ".yaml", ".yml"}:
            records.extend(manifest_records(path))
    for sidecar in (ROOT / "ml").rglob("*.sha256"):
        parts = sidecar.read_text(encoding="ascii", errors="ignore").strip().split()
        if not parts:
            continue
        if len(parts) > 1:
            target = sidecar.parent / parts[1]
        else:
            stem = sidecar.with_suffix("")
            target = next((p for p in (stem.with_suffix(".json"), stem.with_suffix(".yaml"), stem.with_suffix(".yml")) if p.exists()), stem)
        records.append((target, parts[0]))
    audit_paths = {
        "protocol": "ml/experiments/v0_3_10/protocol.yaml",
        "data_access_policy": "ml/experiments/v0_3_10/data_access_policy.yaml",
        "training_campaign": "lab/campaigns/v0_3_10_training.yaml",
        "validation_campaign": "lab/campaigns/v0_3_10_internal_validation.yaml",
        "model_selection_policy": "ml/experiments/v0_3_10/model_selection_policy.yaml",
        "validation_policy": "ml/experiments/v0_3_10/internal_validation_policy.yaml",
        "capture_lock_policy": "ml/experiments/v0_3_10/capture_lock_policy.yaml",
        "candidate_manifest": "ml/experiments/v0_3_10/frozen_candidate_manifest.yaml",
        "capture_manifest": "ml/reports/v0_3_10/capture_manifest.json",
        "validation_lock": "ml/experiments/v0_3_10/validation_lock_manifest.yaml",
        "immutable_prediction": "ml/reports/v0_3_10/validation_predictions.json",
    }
    protocol = yaml.safe_load((ROOT / "ml/audits/v0_3_10_1/audit_protocol.yaml").read_text(encoding="utf-8"))
    for key, relative in audit_paths.items():
        records.append((ROOT / relative, protocol["expected_frozen_hashes"][key]))
    matched = sum(restore(path, expected, changed) for path, expected in records)
    print(json.dumps({"record_count": len(records), "matched_count": matched, "changed_count": len(set(changed))}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

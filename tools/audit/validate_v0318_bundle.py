"""Standalone validation итогового evidence bundle v0.3.18."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "ml/reports/v0_3_18"
MANIFEST = REPORT / "v0_3_18_bundle_manifest.yaml"
DETACHED = REPORT / "v0_3_18_bundle_manifest.sha256"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate() -> dict:
    errors: list[str] = []
    if not MANIFEST.is_file() or not DETACHED.is_file():
        return {"bundle_validator_passed": False, "errors": ["manifest_or_detached_missing"]}
    manifest = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    detached = DETACHED.read_text(encoding="utf-8").split()[0]
    if detached != sha(MANIFEST):
        errors.append("detached_hash_mismatch")
    artifacts = manifest.get("artifacts", [])
    if not artifacts:
        errors.append("artifact_list_empty")
    seen: set[str] = set()
    for row in artifacts:
        relative = row.get("path", "")
        if relative in seen:
            errors.append(f"duplicate_path:{relative}")
            continue
        seen.add(relative)
        if not relative or relative.startswith(("/", "\\")) or ".." in Path(relative).parts:
            errors.append(f"invalid_path:{relative}")
            continue
        path = ROOT / relative
        if not path.is_file():
            errors.append(f"missing:{relative}")
            continue
        if path.stat().st_size != row.get("size"):
            errors.append(f"size:{relative}")
        if sha(path) != row.get("sha256"):
            errors.append(f"sha256:{relative}")
    required = set(manifest.get("required_reports", []))
    missing_required = sorted(required - seen)
    errors.extend(f"required_missing:{item}" for item in missing_required)
    return {
        "bundle_validator_passed": not errors,
        "errors": errors,
        "artifact_count": len(artifacts),
        "required_report_count": len(required),
    }


def main() -> int:
    result = validate()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["bundle_validator_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

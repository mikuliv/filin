"""Формирование детерминированного manifest подтверждающих материалов v0.4.0."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "ml/reports/v0_4_0"
OUTPUT = REPORT / "v0_4_0_bundle_manifest.json"
DETACHED = REPORT / "v0_4_0_bundle_manifest.sha256"
INCLUDE = (
    "incident_reconstruction", "tools/incident_reconstruction", "tools/audit/build_v040_manifest.py",
    "tools/audit/validate_v040_bundle.py", "ml/tests/test_v040_incident_reconstruction.py",
    "docs/experiments/v0_4_0.md", "docs/research/incident-reconstruction.md", "docs/status/v0_4_track.yaml",
    "ml/reports/v0_4_0"
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    files: list[Path] = []
    for raw in INCLUDE:
        path = ROOT / raw
        files.extend(sorted(path.rglob("*")) if path.is_dir() else [path])
    excluded = {OUTPUT.resolve(), DETACHED.resolve()}
    files = [path for path in files if path.is_file() and path.resolve() not in excluded and "__pycache__" not in path.parts]
    entries = [{"path": path.relative_to(ROOT).as_posix(), "sha256": sha(path), "size": path.stat().st_size} for path in sorted(set(files))]
    manifest = {"schema_version": "v0_4_0_bundle_manifest_v1", "stage": "v0.4.0", "artifact_count": len(entries), "artifacts": entries}
    data = json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n"
    OUTPUT.write_bytes(data)
    DETACHED.write_text(hashlib.sha256(data).hexdigest() + "  v0_4_0_bundle_manifest.json\n", encoding="utf-8")
    print(f"artifact_count={len(entries)}")
    return 0


if __name__ == "__main__": raise SystemExit(main())

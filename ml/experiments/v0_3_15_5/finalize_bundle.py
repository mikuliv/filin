from __future__ import annotations

import hashlib
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
REPORT = ROOT / "ml/reports/v0_3_15_5"
MANIFEST = REPORT / "v0_3_15_5_bundle_manifest.yaml"
DETACHED = REPORT / "v0_3_15_5_bundle_manifest.sha256"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    paths = sorted(path for path in REPORT.iterdir() if path.is_file() and path not in {MANIFEST, DETACHED})
    paths += [ROOT / "ml/protocols/v0_3_15_5_protocol.yaml", ROOT / "docs/experiments/v0_3_15_5.md",
              ROOT / "ml/tests/test_v03155_independent_holdout.py", ROOT / "tools/audit/validate_v03155_bundle.py",
              ROOT / "tools/audit/validate_v03155_artifacts.py"]
    artifacts = []
    for path in paths:
        relative = path.relative_to(ROOT).as_posix()
        artifacts.append({"role": path.stem, "relative_path": relative, "size": path.stat().st_size,
                          "sha256": sha(path), "schema_version": "v03155_bundle_entry_v1", "required": True,
                          "creation_phase": "after_label_unlock" if "protocol" not in path.name and "lock" not in path.name else "before_label_unlock",
                          "before_or_after_label_unlock": "after" if "protocol" not in path.name and "lock" not in path.name else "before",
                          "candidate_scope": "v03154:65a3dd912d845bc1", "producing_command": "python -m ml.experiments.v0_3_15_5.finalize_bundle",
                          "claim_ids": [], "contains_sensitive_data": False, "git_inclusion_permitted": True})
    value = {"schema_version": "v03155_bundle_manifest_v1", "stage": "v0.3.15.5", "immutable": True,
             "artifact_count": len(artifacts), "artifacts": artifacts}
    MANIFEST.write_text(yaml.safe_dump(value, allow_unicode=True, sort_keys=False), encoding="utf-8", newline="\n")
    DETACHED.write_text(f"{sha(MANIFEST)}  {MANIFEST.name}\n", encoding="ascii", newline="\n")
    print(sha(MANIFEST))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


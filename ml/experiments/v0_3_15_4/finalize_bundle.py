from __future__ import annotations

import hashlib
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[3]
REPORT = ROOT / "ml/reports/v0_3_15_4"
MANIFEST = REPORT / "v0_3_15_4_bundle_manifest.yaml"
DETACHED = REPORT / "v0_3_15_4_bundle_manifest.sha256"


def sha(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    paths = [path for path in sorted(REPORT.iterdir()) if path.is_file() and path not in {MANIFEST, DETACHED}]
    paths += [
        ROOT / "ml/protocols/v0_3_15_4_protocol.yaml", ROOT / "ml/artifacts/v0_3_15_4/candidate_manifest.json",
        ROOT / "ml/experiments/v0_3_15_4/feature_contract_v2.yaml", ROOT / "ml/experiments/v0_3_15_4/scenario_contracts.yaml",
        ROOT / "ml/experiments/v0_3_15_4/training_lock.json", ROOT / "ml/experiments/v0_3_15_4/pre_audit_lock.json",
        ROOT / "docs/experiments/v0_3_15_4.md", ROOT / "docs/status/project-status.yaml",
        ROOT / "ml/tests/test_v03154_controlled_redevelopment.py", ROOT / "tools/audit/validate_v03154_artifacts.py",
        ROOT / "tools/audit/validate_v03154_bundle.py",
    ]
    artifacts=[]
    for path in paths:
        relative=path.relative_to(ROOT).as_posix()
        artifacts.append({"role": path.stem, "path": relative, "size": path.stat().st_size, "sha256": sha(path), "required": True, "contains_sensitive_data": False, "git_inclusion_permitted": True})
    value={"schema_version":"v03154_bundle_v1","stage":"v0.3.15.4","artifact_count":len(artifacts),"historical_anchors":{"v03152_bundle_manifest_sha256":"49e13eceb44873f593844b07d86215b36dffd96be7ebbbb75a004c08bad8dcda","v03153_bundle_manifest_sha256":"20ad130d2a30a7a495c6a2b82e189e9c030a4ee1f03d84f661cd21909c88a3c2"},"raw_artifacts_included":False,"artifacts":artifacts}
    MANIFEST.write_text(yaml.safe_dump(value,allow_unicode=True,sort_keys=False),encoding="utf-8",newline="\n")
    DETACHED.write_text(f"{sha(MANIFEST)}  {MANIFEST.name}\n",encoding="utf-8",newline="\n")
    print(f"artifact_count={len(artifacts)} manifest_sha256={sha(MANIFEST)}")
    return 0


if __name__ == "__main__": raise SystemExit(main())

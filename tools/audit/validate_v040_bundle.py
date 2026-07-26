"""Проверка manifest, frozen identity и representative bundle v0.4.0."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from incident_reconstruction.validation import validate_bundle  # noqa: E402


def main() -> int:
    report = ROOT / "ml/reports/v0_4_0"
    manifest_path = report / "v0_4_0_bundle_manifest.json"
    detached = (report / "v0_4_0_bundle_manifest.sha256").read_text(encoding="utf-8").split()[0]
    errors: list[str] = []
    if hashlib.sha256(manifest_path.read_bytes()).hexdigest() != detached: errors.append("detached_manifest_mismatch")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for item in manifest["artifacts"]:
        path = ROOT / item["path"]
        if not path.is_file(): errors.append("missing:" + item["path"]); continue
        if path.stat().st_size != item["size"] or hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]: errors.append("mismatch:" + item["path"])
    try: validate_bundle(json.loads((report / "representative_reconstruction_bundle.json").read_text(encoding="utf-8")))
    except Exception as error: errors.append("representative_bundle:" + str(error))
    policy = json.loads((report / "v0_4_0_policy_result.json").read_text(encoding="utf-8"))
    if not policy.get("v0_4_0_stage_passed") or policy.get("candidate_id") != "v03154:65a3dd912d845bc1": errors.append("policy_result_invalid")
    result = {"bundle_validator_passed": not errors, "artifact_count": manifest["artifact_count"], "errors": errors}
    print(json.dumps(result, ensure_ascii=False, indent=2)); return 0 if not errors else 1


if __name__ == "__main__": raise SystemExit(main())

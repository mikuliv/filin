from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

import yaml


class BundleError(RuntimeError):
    pass


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate(manifest: Path, detached: Path, root: Path) -> dict:
    expected = detached.read_text(encoding="utf-8").split()[0]
    if expected != sha(manifest): raise BundleError("detached_sha_mismatch")
    value = yaml.safe_load(manifest.read_text(encoding="utf-8"))
    if value.get("schema_version") != "v0316_bundle_manifest_v1" or value.get("stage") != "v0.3.16" or value.get("revision") != 2: raise BundleError("manifest_identity_invalid")
    artifacts = value.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts: raise BundleError("artifacts_missing")
    paths, roles = set(), set()
    for item in artifacts:
        relative = item.get("relative_path", "")
        path = Path(relative)
        if path.is_absolute() or ".." in path.parts or re.match(r"^[A-Za-z]:", relative): raise BundleError("path_confinement")
        if relative in paths: raise BundleError("duplicate_path")
        paths.add(relative); roles.add(item.get("artifact_role"))
        target = (root / path).resolve()
        if root.resolve() not in target.parents or not target.is_file(): raise BundleError("artifact_missing")
        if target.stat().st_size != item.get("size") or sha(target) != item.get("sha256"): raise BundleError("artifact_integrity")
        if item.get("contains_sensitive_data") or not item.get("git_inclusion_permitted"): raise BundleError("sensitive_artifact")
    required = {"protocol", "v0_3_16_policy_result", "historical_integrity_report", "candidate_identity_anchor", "network_topology_report", "certificate_manifest", "campaign_manifest", "prediction_integrity_report", "source_connector_receiver_reconciliation", "hash_chain_report", "claim_evidence_ledger", "promotion_decision"}
    if required - roles: raise BundleError("required_roles_missing")
    policy_path = root / "ml/reports/v0_3_16/v0_3_16_policy_result.json"
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    if not policy["v0316_stage_passed"] or not policy["candidate_ready_for_v0_3_17_controlled_local_shadow_rehearsal"]: raise BundleError("readiness_invalid")
    if any(policy[key] for key in ("candidate_ready_for_shadow_mode", "backend_integration_allowed", "shadow_mode_allowed", "production_ready")): raise BundleError("prohibition_invalid")
    tracked = subprocess_files(root)
    forbidden_suffixes = {".pcap", ".pcapng", ".sqlite", ".db", ".key"}
    if any(Path(name).suffix.casefold() in forbidden_suffixes or "runtime/v0_3_16/" in name.replace("\\", "/") for name in tracked): raise BundleError("raw_artifact_tracked")
    if any("key.pem" in name.casefold() for name in tracked): raise BundleError("private_key_tracked")
    return {"bundle_validator_passed": True, "artifact_count": len(artifacts), "required_role_count": len(required), "detached_sha256": expected}


def subprocess_files(root: Path) -> list[str]:
    import subprocess
    return subprocess.check_output(["git", "ls-files"], cwd=root, text=True).splitlines()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--detached", type=Path, required=True)
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args()
    print(json.dumps(validate(args.manifest, args.detached, args.root.resolve()), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

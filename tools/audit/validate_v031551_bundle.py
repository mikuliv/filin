from __future__ import annotations

import argparse
import hashlib
import re
from pathlib import Path

import yaml

REQUIRED_ROLES = {"policy_result", "protocol", "scientific_evidence_anchor", "shadow_event_v1_integrity", "shadow_event_v2_schema", "candidate_registry", "candidate_registry_commitment", "candidate_runtime_lock", "campaign_manifest", "prediction_manifest", "event_set", "hash_chain", "claim_evidence_ledger", "composite_promotion", "resume_integrity", "completion_marker"}
RAW_SUFFIXES = {".pcap", ".pcapng", ".joblib", ".pkl", ".onnx"}


class BundleError(ValueError):
    pass


def sha(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()


def validate(manifest_path: Path, detached_path: Path, root: Path) -> dict:
    root = root.resolve(); manifest_path = manifest_path.resolve(); detached_path = detached_path.resolve()
    expected = detached_path.read_text(encoding="utf-8").split()[0]
    if expected != sha(manifest_path): raise BundleError("detached_sha_mismatch")
    value = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    if value.get("schema_version") != "v031551_bundle_manifest_v1": raise BundleError("unknown_schema_version")
    artifacts = value.get("artifacts")
    if not isinstance(artifacts, list): raise BundleError("manifest_syntax")
    paths = [item.get("path") for item in artifacts]
    if len(paths) != len(set(paths)): raise BundleError("duplicate_path")
    roles = {item.get("role") for item in artifacts}
    if not REQUIRED_ROLES.issubset(roles): raise BundleError("missing_required_role")
    for item in artifacts:
        relative = Path(item["path"])
        if relative.is_absolute(): raise BundleError("absolute_path")
        target = (root / relative).resolve()
        try: target.relative_to(root)
        except ValueError: raise BundleError("path_traversal")
        if not target.is_file(): raise BundleError("missing_artifact")
        if target.stat().st_size != item["size"]: raise BundleError("artifact_size_mismatch")
        if sha(target) != item["sha256"]: raise BundleError("artifact_hash_mismatch")
        if target.suffix.casefold() in RAW_SUFFIXES or item.get("contains_sensitive_data") is True or item.get("git_inclusion_permitted") is not True:
            raise BundleError("raw_artifact_in_bundle")
        text = target.read_text(encoding="utf-8", errors="ignore")
        if re.search(r"[A-Za-z]:\\Users\\[^\\]+", text): raise BundleError("absolute_user_path")
    anchors = value.get("integrity_anchors", {})
    by_role = {item["role"]: item for item in artifacts}
    for key, role in (("scientific_evidence_anchor_sha256", "scientific_evidence_anchor"), ("shadow_event_v2_sha256", "shadow_event_v2_schema"), ("candidate_registry_sha256", "candidate_registry"), ("candidate_registry_commitment_artifact_sha256", "candidate_registry_commitment"), ("candidate_runtime_lock_sha256", "candidate_runtime_lock"), ("prediction_manifest_sha256", "prediction_manifest"), ("claim_evidence_ledger_sha256", "claim_evidence_ledger")):
        if anchors.get(key) != by_role[role]["sha256"]: raise BundleError("integrity_anchor_mismatch")
    return {"bundle_validator_passed": True, "artifact_count": len(artifacts), "required_roles_passed": True, "path_confinement_passed": True, "artifact_exclusion_passed": True, "manifest_sha256": sha(manifest_path)}


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--manifest", required=True); parser.add_argument("--detached", required=True); parser.add_argument("--root", default=".")
    args = parser.parse_args(); print(yaml.safe_dump(validate(Path(args.manifest), Path(args.detached), Path(args.root)), sort_keys=True)); return 0


if __name__ == "__main__": raise SystemExit(main())

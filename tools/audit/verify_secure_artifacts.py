"""Verify external artifacts without exposing the secure-root path."""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.audit.artifact_hashes import file_sha256


def verify(root: str | None, descriptor_path: Path) -> dict:
    if not root:
        return {"status": "secure_artifacts_not_available", "passed": False, "reason": "FILIN_SECURE_ARTIFACT_ROOT_unavailable"}
    descriptor = yaml.safe_load(descriptor_path.read_text(encoding="utf-8"))
    relative = Path(descriptor["artifact_relative_path"])
    if relative.is_absolute() or ".." in relative.parts:
        return {"status": "failed", "passed": False, "reason": "unsafe_artifact_reference"}
    artifact = Path(root).resolve() / relative
    if not artifact.is_file():
        return {"status": "failed", "passed": False, "reason": "referenced_artifact_missing"}
    actual = file_sha256(artifact); expected = str(descriptor["expected_artifact_sha256"])
    passed = bool(re.fullmatch(r"[0-9a-f]{64}", expected)) and actual == expected
    return {"status": "passed" if passed else "failed", "passed": passed,
            "reason": "artifact_hash_matches" if passed else "artifact_hash_mismatch",
            "artifact_type": descriptor["artifact_type"], "sensitive_content_excluded": True}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=None); parser.add_argument("--descriptor", default="ml/experiments/post_v037_audit/secure_artifact_reference.yaml")
    parser.add_argument("--strict", action="store_true"); args = parser.parse_args()
    result = verify(args.root or os.environ.get("FILIN_SECURE_ARTIFACT_ROOT"), Path(args.descriptor))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.strict and result["status"] == "failed": raise SystemExit(1)


if __name__ == "__main__": main()

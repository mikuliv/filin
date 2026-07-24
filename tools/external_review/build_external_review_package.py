"""Детерминированная сборка review/reproducibility package v0.3.18."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
from pathlib import Path
from typing import Any

from tools.external_review.canonical_commitment import (
    CommitmentError,
    canonical_bytes,
    manifest_root,
    normalize_relative_path,
)


ROOT = Path(__file__).resolve().parents[2]
FORBIDDEN_SUFFIXES = {
    ".pcap", ".pcapng", ".joblib", ".sqlite", ".db", ".wal", ".key",
    ".pem", ".pfx", ".zip", ".7z", ".tar", ".gz",
}
MAX_FILE_SIZE = 2 * 1024 * 1024
BASE_ALLOWLIST = [
    "ml/protocols/v0_3_18_external_review_protocol.yaml",
    "tools/external_review/canonical_commitment.py",
    "tools/external_review/verify_external_review_package.py",
    "tools/external_review/frozen_evaluator.py",
]


class PackageBuildError(ValueError):
    pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _is_reparse_point(path: Path) -> bool:
    if path.is_symlink():
        return True
    attributes = getattr(path.stat(follow_symlinks=False), "st_file_attributes", 0)
    return bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))


def package_allowlist(root: Path = ROOT) -> list[str]:
    paths = list(BASE_ALLOWLIST)
    for directory in ("external_review/contracts", "docs/external_review"):
        base = root / directory
        if base.is_dir():
            paths.extend(
                path.relative_to(root).as_posix()
                for path in sorted(base.rglob("*"))
                if path.is_file()
            )
    return sorted(set(paths))


def validate_source(path: Path, relative: str) -> None:
    normalize_relative_path(relative)
    if _is_reparse_point(path):
        raise PackageBuildError(f"reparse_point_rejected:{relative}")
    if path.suffix.lower() in FORBIDDEN_SUFFIXES:
        raise PackageBuildError(f"forbidden_suffix:{relative}")
    size = path.stat().st_size
    if size > MAX_FILE_SIZE:
        raise PackageBuildError(f"file_too_large:{relative}")
    raw = path.read_bytes()
    if b"\x00" not in raw:
        text = raw.decode("utf-8")
        local_markers = tuple(f"{drive}:{chr(92)}" for drive in ("G", "H")) + ("/" + "home/",)
        if any(marker in text for marker in local_markers):
            raise PackageBuildError(f"absolute_local_path:{relative}")
        lowered = text.casefold()
        for marker in ("private_key", "begin rsa private key", "password=", "api_key="):
            if marker in lowered:
                raise PackageBuildError(f"secret_marker:{relative}")


def build_package(
    destination: Path,
    *,
    candidate_commitment: str,
    protocol_commitment: str,
    evaluator_commitment: str,
    root: Path = ROOT,
) -> dict[str, Any]:
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)
    entries: list[dict[str, Any]] = []
    for relative in package_allowlist(root):
        source = root / Path(*relative.split("/"))
        if not source.is_file():
            raise PackageBuildError(f"allowlisted_file_missing:{relative}")
        validate_source(source, relative)
        target = destination / Path(*relative.split("/"))
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        os.utime(target, (0, 0))
        entries.append({"path": relative, "sha256": sha256(target), "size": target.stat().st_size})
    manifest = {
        "schema_version": "external_review_runtime_package_manifest_v1",
        "package_role": "review_and_reproducibility",
        "package_version": "v0.3.18",
        "candidate_commitment": candidate_commitment,
        "protocol_commitment": protocol_commitment,
        "evaluator_commitment": evaluator_commitment,
        "normalization": "sorted_paths_content_hashes_mtime_zero",
        "files": sorted(entries, key=lambda item: item["path"]),
    }
    manifest["root_commitment"] = manifest_root(manifest["files"])
    (destination / "package_manifest.json").write_bytes(canonical_bytes(manifest) + b"\n")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("destination", type=Path)
    parser.add_argument("--candidate-commitment", required=True)
    parser.add_argument("--protocol-commitment", required=True)
    parser.add_argument("--evaluator-commitment", required=True)
    args = parser.parse_args()
    try:
        manifest = build_package(
            args.destination,
            candidate_commitment=args.candidate_commitment,
            protocol_commitment=args.protocol_commitment,
            evaluator_commitment=args.evaluator_commitment,
        )
    except (PackageBuildError, CommitmentError, OSError, UnicodeError) as error:
        print(json.dumps({"package_build_passed": False, "error": str(error)}))
        return 1
    print(json.dumps({"package_build_passed": True, "root_commitment": manifest["root_commitment"], "file_count": len(manifest["files"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

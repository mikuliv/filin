"""Standalone verifier review package; использует только Python stdlib."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path, PurePosixPath
from typing import Any


SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
WINDOWS_ABSOLUTE_RE = re.compile(r"^[A-Za-z]:[\\/]")
FORBIDDEN_SUFFIXES = {
    ".pcap", ".pcapng", ".joblib", ".sqlite", ".db", ".wal", ".key",
    ".pem", ".pfx", ".zip", ".7z", ".tar", ".gz",
}


def _no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate_json_key:{key}")
        result[key] = value
    return result


def strict_load(path: Path) -> Any:
    return json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=_no_duplicates,
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError(f"non_finite:{value}")),
    )


def canonical(value: Any) -> bytes:
    def check(item: Any) -> None:
        if isinstance(item, float) and not math.isfinite(item):
            raise ValueError("non_finite")
        if isinstance(item, list):
            for child in item: check(child)
        if isinstance(item, dict):
            for child in item.values(): check(child)
    check(value)
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")


def normalize(raw: str) -> str:
    if not raw or WINDOWS_ABSOLUTE_RE.match(raw) or raw.startswith(("/", "\\", "//", "\\\\")):
        raise ValueError("absolute_or_empty_path")
    path = PurePosixPath(raw.replace("\\", "/"))
    if any(part in ("", ".", "..") for part in path.parts):
        raise ValueError("path_traversal")
    return path.as_posix()


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def root_hash(entries: list[dict[str, Any]]) -> str:
    normalized = sorted(
        [{"path": normalize(row["path"]), "sha256": row["sha256"], "size": row["size"]} for row in entries],
        key=lambda row: row["path"],
    )
    return hashlib.sha256(canonical(normalized)).hexdigest()


def verify(package: Path) -> dict[str, Any]:
    errors: list[str] = []
    manifest_path = package / "package_manifest.json"
    try:
        manifest = strict_load(manifest_path)
    except Exception as error:
        return {"package_verification_passed": False, "errors": [f"manifest:{type(error).__name__}:{error}"]}
    required = {
        "schema_version", "package_role", "package_version", "candidate_commitment",
        "protocol_commitment", "evaluator_commitment", "normalization", "files",
        "root_commitment",
    }
    if set(manifest) != required:
        errors.append("manifest_schema")
    for key in ("candidate_commitment", "protocol_commitment", "evaluator_commitment", "root_commitment"):
        if not SHA256_RE.fullmatch(str(manifest.get(key, ""))):
            errors.append(f"invalid_commitment:{key}")
    declared: set[str] = set()
    for row in manifest.get("files", []):
        try:
            relative = normalize(str(row["path"]))
        except (KeyError, ValueError) as error:
            errors.append(f"invalid_path:{error}")
            continue
        if relative in declared:
            errors.append(f"duplicate_path:{relative}")
            continue
        declared.add(relative)
        path = package / Path(*relative.split("/"))
        if path.is_symlink():
            errors.append(f"symlink:{relative}")
        if path.suffix.lower() in FORBIDDEN_SUFFIXES:
            errors.append(f"forbidden_file:{relative}")
        if not path.is_file():
            errors.append(f"missing_file:{relative}")
            continue
        if path.stat().st_size != row.get("size"):
            errors.append(f"size_mismatch:{relative}")
        if file_sha(path) != row.get("sha256"):
            errors.append(f"hash_mismatch:{relative}")
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            text = ""
        local_markers = tuple(f"{drive}:{chr(92)}" for drive in ("G", "H")) + ("/" + "home/",)
        if any(marker in text for marker in local_markers):
            errors.append(f"absolute_local_path:{relative}")
    actual = {
        path.relative_to(package).as_posix()
        for path in package.rglob("*")
        if path.is_file() and path != manifest_path
    }
    for extra in sorted(actual - declared):
        errors.append(f"undeclared_file:{extra}")
    for missing in sorted(declared - actual):
        errors.append(f"declared_file_absent:{missing}")
    try:
        if root_hash(manifest.get("files", [])) != manifest.get("root_commitment"):
            errors.append("root_commitment_mismatch")
    except Exception as error:
        errors.append(f"root_commitment_invalid:{error}")
    return {
        "schema_version": "external_review_package_verification_v1",
        "package_verification_passed": not errors,
        "standalone": True,
        "git_history_used": False,
        "network_used": False,
        "backend_used": False,
        "file_count": len(declared),
        "root_commitment": manifest.get("root_commitment"),
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("package", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = verify(args.package)
    text = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8", newline="\n")
    print(text, end="")
    return 0 if result["package_verification_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

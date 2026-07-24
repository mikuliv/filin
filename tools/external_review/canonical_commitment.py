"""Канонические JSON commitments для протокола внешней проверки."""
from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path, PurePosixPath
from typing import Any, Iterable


SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
WINDOWS_ABSOLUTE_RE = re.compile(r"^[A-Za-z]:[\\/]")


class CommitmentError(ValueError):
    """Ошибка canonical serialization или confinement."""


def _object_no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise CommitmentError(f"duplicate_json_key:{key}")
        result[key] = value
    return result


def load_json_strict(raw: str | bytes) -> Any:
    """Загрузить JSON, запретив duplicate keys и нечисловые константы."""
    if isinstance(raw, bytes):
        try:
            raw = raw.decode("utf-8")
        except UnicodeDecodeError as error:
            raise CommitmentError("json_not_utf8") from error

    def reject_constant(value: str) -> None:
        raise CommitmentError(f"non_finite_number:{value}")

    try:
        value = json.loads(
            raw,
            object_pairs_hook=_object_no_duplicates,
            parse_constant=reject_constant,
        )
    except CommitmentError:
        raise
    except (json.JSONDecodeError, TypeError) as error:
        raise CommitmentError("invalid_json") from error
    validate_json_value(value)
    return value


def validate_json_value(value: Any, pointer: str = "$") -> None:
    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise CommitmentError(f"non_finite_number:{pointer}")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            validate_json_value(item, f"{pointer}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise CommitmentError(f"non_string_key:{pointer}")
            validate_json_value(item, f"{pointer}.{key}")
        return
    raise CommitmentError(f"unsupported_json_type:{pointer}")


def canonical_bytes(value: Any) -> bytes:
    validate_json_value(value)
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def commitment_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def commitment_receipt(value: Any, *, subject: str, parents: Iterable[str] = ()) -> dict[str, Any]:
    parent_list = sorted(set(parents))
    if any(not SHA256_RE.fullmatch(item) for item in parent_list):
        raise CommitmentError("invalid_parent_commitment")
    return {
        "schema_version": "canonical_commitment_receipt_v1",
        "subject": subject,
        "canonicalization": "utf8_json_sorted_keys_compact",
        "digest_algorithm": "sha256",
        "commitment_sha256": commitment_sha256(value),
        "parent_commitments": parent_list,
        "hash_commitment_is_digital_signature": False,
    }


def normalize_relative_path(raw: str) -> str:
    if not raw or "\x00" in raw:
        raise CommitmentError("invalid_path")
    if WINDOWS_ABSOLUTE_RE.match(raw) or raw.startswith(("/", "\\", "//", "\\\\")):
        raise CommitmentError("absolute_path")
    normalized = raw.replace("\\", "/")
    path = PurePosixPath(normalized)
    if any(part in ("", ".", "..") for part in path.parts):
        raise CommitmentError("path_traversal")
    return path.as_posix()


def confined_path(root: Path, raw: str) -> Path:
    normalized = normalize_relative_path(raw)
    root = root.resolve()
    target = (root / Path(*PurePosixPath(normalized).parts)).resolve()
    try:
        target.relative_to(root)
    except ValueError as error:
        raise CommitmentError("path_escapes_root") from error
    return target


def scan_for_absolute_paths(value: Any, pointer: str = "$") -> list[str]:
    findings: list[str] = []
    if isinstance(value, str):
        if WINDOWS_ABSOLUTE_RE.match(value) or value.startswith(("/", "\\\\", "//")):
            findings.append(pointer)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            findings.extend(scan_for_absolute_paths(item, f"{pointer}[{index}]"))
    elif isinstance(value, dict):
        for key, item in value.items():
            findings.extend(scan_for_absolute_paths(item, f"{pointer}.{key}"))
    return findings


def manifest_root(files: Iterable[dict[str, Any]]) -> str:
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for entry in files:
        path = normalize_relative_path(str(entry["path"]))
        digest = str(entry["sha256"])
        size = int(entry["size"])
        if path in seen:
            raise CommitmentError(f"duplicate_manifest_path:{path}")
        if not SHA256_RE.fullmatch(digest) or size < 0:
            raise CommitmentError(f"invalid_manifest_entry:{path}")
        seen.add(path)
        normalized.append({"path": path, "sha256": digest, "size": size})
    return commitment_sha256(sorted(normalized, key=lambda item: item["path"]))


def verify_receipt(value: Any, receipt: dict[str, Any]) -> bool:
    return (
        receipt.get("schema_version") == "canonical_commitment_receipt_v1"
        and receipt.get("digest_algorithm") == "sha256"
        and receipt.get("commitment_sha256") == commitment_sha256(value)
        and receipt.get("hash_commitment_is_digital_signature") is False
    )

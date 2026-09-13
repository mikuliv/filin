"""Fail-closed доступ к каноническим байтам Git blob."""
from __future__ import annotations

import hashlib
import re
import subprocess
from pathlib import Path, PurePosixPath


class GitObjectError(RuntimeError):
    """Канонический объект Git недоступен или задан неоднозначно."""


def _relative_path(path: str) -> str:
    normalized = path.replace("\\", "/")
    parsed = PurePosixPath(normalized)
    if not normalized or parsed.is_absolute() or ".." in parsed.parts or ":" in normalized:
        raise GitObjectError(f"git_path_invalid:{path}")
    return normalized


def _git_commit(root_text: str, revision: str) -> str:
    if not revision:
        raise GitObjectError("git_revision_missing")
    result = subprocess.run(
        ["git", "rev-parse", "--verify", f"{revision}^{{commit}}"],
        cwd=root_text,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if result.returncode:
        raise GitObjectError(f"git_commit_unavailable:{revision}")
    return result.stdout.strip()


def git_commit(root: Path, revision: str) -> str:
    return _git_commit(str(root.resolve()), revision)


def git_tree(root: Path, revision: str) -> str:
    if not revision:
        raise GitObjectError("git_revision_missing")
    result = subprocess.run(
        ["git", "rev-parse", "--verify", f"{revision}^{{tree}}"],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if result.returncode:
        raise GitObjectError(f"git_tree_unavailable:{revision}")
    return result.stdout.strip()


_BLOB_SHA_CACHE: dict[tuple[str, str, str], str] = {}


def git_blob_sha256_many(root: Path, paths: list[str], revision: str = "HEAD") -> dict[str, str]:
    root_text = str(root.resolve())
    commit = revision if re.fullmatch(r"[0-9a-f]{40}", revision) else git_tree(root, revision)
    normalized = [_relative_path(path) for path in paths]
    result: dict[str, str] = {}
    missing: list[str] = []
    for path in normalized:
        cached = _BLOB_SHA_CACHE.get((root_text, commit, path))
        if cached is None:
            missing.append(path)
        else:
            result[path] = cached
    if missing:
        request = b"".join(f"{commit}:{path}\n".encode("utf-8") for path in missing)
        process = subprocess.run(
            ["git", "cat-file", "--batch"], cwd=root_text, input=request, capture_output=True
        )
        if process.returncode:
            raise GitObjectError(f"git_batch_failed:{commit}")
        output = process.stdout
        offset = 0
        for path in missing:
            end = output.find(b"\n", offset)
            if end < 0:
                raise GitObjectError(f"git_batch_malformed:{commit}:{path}")
            header = output[offset:end]
            offset = end + 1
            if header.endswith(b" missing"):
                raise GitObjectError(f"git_blob_unavailable:{commit}:{path}")
            fields = header.rsplit(b" ", 2)
            if len(fields) != 3 or fields[1] != b"blob":
                raise GitObjectError(f"git_object_not_blob:{commit}:{path}")
            size = int(fields[2])
            content = output[offset:offset + size]
            offset += size + 1
            digest = hashlib.sha256(content).hexdigest()
            _BLOB_SHA_CACHE[(root_text, commit, path)] = digest
            result[path] = digest
    return result


def git_index_tree(root: Path) -> str:
    result = subprocess.run(
        ["git", "write-tree"], cwd=root, capture_output=True, text=True, encoding="utf-8"
    )
    if result.returncode:
        raise GitObjectError("git_index_tree_unavailable")
    return result.stdout.strip()


def git_index_blob_sha256_many(root: Path, paths: list[str]) -> dict[str, str]:
    return git_blob_sha256_many(root, paths, git_index_tree(root))


def git_blob_bytes(root: Path, path: str, revision: str = "HEAD") -> bytes:
    relative = _relative_path(path)
    commit = git_commit(root, revision)
    result = subprocess.run(
        ["git", "cat-file", "blob", f"{commit}:{relative}"],
        cwd=root,
        capture_output=True,
    )
    if result.returncode:
        raise GitObjectError(f"git_blob_unavailable:{commit}:{relative}")
    return result.stdout


def git_blob_sha256(root: Path, path: str, revision: str = "HEAD") -> str:
    relative = _relative_path(path)
    return git_blob_sha256_many(root, [relative], revision)[relative]

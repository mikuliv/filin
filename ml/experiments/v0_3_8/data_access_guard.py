"""Fail-closed контроль доступа к данным нового цикла v0.3.8."""
from __future__ import annotations

import hashlib
import json
import os
import stat
from pathlib import Path

import yaml


class DataAccessError(PermissionError):
    pass


class DataAccessGuard:
    def __init__(self, root: Path, policy_path: Path, audit_path: Path | None = None):
        self.root = root.resolve(strict=True)
        self.policy = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
        self.audit_path = audit_path
        self.accesses: list[dict] = []

    def _relative(self, path: Path) -> tuple[Path, str]:
        original = Path(path)
        candidate = original if original.is_absolute() else self.root / original
        current = candidate
        while current != self.root and self.root in current.parents:
            if current.exists():
                attributes = current.stat(follow_symlinks=False).st_file_attributes if os.name == "nt" else 0
                if current.is_symlink() or bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)):
                    raise DataAccessError("Symlink или junction запрещён")
            current = current.parent
        resolved = candidate.resolve(strict=True)
        if self.root not in (resolved, *resolved.parents):
            raise DataAccessError("Путь вне workspace запрещён")
        return resolved, resolved.relative_to(self.root).as_posix()

    def open_dataset(self, path: Path, *, purpose: str, candidate_frozen: bool = False,
                     validation_locked: bool = False):
        resolved, relative = self._relative(path)
        lower = relative.lower()
        forbidden = [str(value).lower() for value in self.policy.get("forbidden_roots", []) + self.policy.get("forbidden_path_fragments", [])]
        if any(value in lower for value in forbidden):
            raise DataAccessError(f"Запрещённый источник: {relative}")
        digest = hashlib.sha256(resolved.read_bytes()).hexdigest()
        if digest in set(self.policy.get("forbidden_source_sha256", [])):
            raise DataAccessError(f"Запрещённая копия по SHA-256: {relative}")
        validation = purpose.startswith("validation_")
        if validation and not candidate_frozen:
            raise DataAccessError("Validation rows запрещены до candidate freeze")
        if purpose in {"validation_labels", "validation_predictions"} and not validation_locked:
            raise DataAccessError("Validation labels/predictions запрещены до validation lock")
        allowed = self.policy["allowed_validation_sources" if validation else "allowed_training_sources"]
        if not any(prefix in relative for prefix in allowed):
            raise DataAccessError(f"Источник не входит в allowlist: {relative}")
        event = {"path": relative, "sha256": digest, "purpose": purpose, "candidate_frozen": candidate_frozen, "validation_locked": validation_locked}
        self.accesses.append(event)
        self.save()
        return resolved.open("r", encoding="utf-8")

    def audit(self) -> dict:
        return {
            "v038_data_access_valid": True,
            "accesses": self.accesses,
            "v036_rows_loaded": False,
            "v037_rows_loaded": False,
            "v037_predictions_loaded": False,
            "v037_labels_loaded": False,
            "model_trained_on_v036_data": False,
            "model_trained_on_v037_data": False,
        }

    def save(self) -> None:
        if self.audit_path:
            self.audit_path.parent.mkdir(parents=True, exist_ok=True)
            self.audit_path.write_text(json.dumps(self.audit(), ensure_ascii=False, indent=2), encoding="utf-8")

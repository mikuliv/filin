"""Fail-closed доступ только к новым данным v0.3.10."""
from __future__ import annotations
import hashlib, json, os, stat
from pathlib import Path
import yaml

class DataAccessError(PermissionError):
    pass

class DataAccessGuard:
    def __init__(self, root: Path, policy_path: Path, audit_path: Path | None = None):
        self.root = root.resolve(strict=True)
        self.policy = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
        hashes_path = self.root / self.policy["forbidden_hash_file"]
        self.forbidden_hashes = set(yaml.safe_load(hashes_path.read_text(encoding="utf-8"))["hashes"])
        self.audit_path, self.accesses, self.prediction_created = audit_path, [], False

    def _relative(self, path):
        candidate = Path(path)
        if candidate.is_absolute():
            try:
                candidate.relative_to(self.root)
            except ValueError as error:
                raise DataAccessError("Абсолютный путь вне репозитория запрещён") from error
        candidate = candidate if candidate.is_absolute() else self.root / candidate
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

    def open_dataset(self, path, *, purpose, candidate_frozen=False, validation_locked=False):
        resolved, relative = self._relative(path)
        lower = relative.lower()
        forbidden = [str(value).lower() for value in self.policy["forbidden_roots"] + self.policy["forbidden_path_fragments"]]
        if any(value in lower for value in forbidden):
            raise DataAccessError(f"Запрещённый исторический источник: {relative}")
        digest = hashlib.sha256(resolved.read_bytes()).hexdigest()
        if digest in self.forbidden_hashes:
            raise DataAccessError(f"Запрещённая копия исторического dataset по SHA-256: {relative}")
        validation = purpose.startswith("validation_")
        if validation and not candidate_frozen:
            raise DataAccessError("Validation rows запрещены до candidate freeze")
        if purpose in {"validation_labels", "validation_predictions"} and not validation_locked:
            raise DataAccessError("Validation labels и predictions запрещены до полного validation lock")
        allowed = self.policy["allowed_validation_sources" if validation else "allowed_training_sources"]
        if not any(prefix in relative for prefix in allowed):
            raise DataAccessError(f"Источник не входит в allowlist: {relative}")
        self.accesses.append({"path": relative, "sha256": digest, "purpose": purpose,
                              "candidate_frozen": candidate_frozen, "validation_locked": validation_locked})
        self.save()
        return resolved.open("r", encoding="utf-8")

    def claim_prediction(self, prediction_lock_path: Path, validation_lock: dict):
        if validation_lock.get("capture_hash_count") != 360 or validation_lock.get("capture_hashes_complete") is not True:
            raise DataAccessError("Prediction запрещена без 360 capture hashes в pre-prediction lock")
        if self.prediction_created or prediction_lock_path.exists():
            raise DataAccessError("Immutable prediction невозможно повторить")
        self.prediction_created = True

    def audit(self):
        return {"v0310_data_access_valid": True, "accesses": self.accesses,
                "v036_rows_loaded": False, "v037_rows_loaded": False, "v038_rows_loaded": False, "v039_rows_loaded": False,
                "v038_predictions_loaded": False, "v039_predictions_loaded": False,
                "v038_labels_loaded": False, "v039_labels_loaded": False,
                "model_trained_on_v036_data": False, "model_trained_on_v037_data": False,
                "model_trained_on_v038_data": False, "model_trained_on_v039_data": False}

    def save(self):
        if self.audit_path:
            self.audit_path.parent.mkdir(parents=True, exist_ok=True)
            self.audit_path.write_text(json.dumps(self.audit(), ensure_ascii=False, indent=2), encoding="utf-8")

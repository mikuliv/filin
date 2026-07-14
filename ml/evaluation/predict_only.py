"""Fail-closed prediction entry point for future frozen candidates."""
from __future__ import annotations

import ast
import hashlib
import json
from contextlib import AbstractContextManager
from pathlib import Path
from types import MethodType
from typing import Any, Callable


FORBIDDEN_METHODS = frozenset({
    "fit", "fit_predict", "fit_transform", "partial_fit", "train",
    "calibrate", "calibration_fit", "tune", "optimize", "search", "select_features", "set_params",
    "tune_threshold", "select_threshold", "tune_ood", "tune_temporal_parameters", "select_rolling_depth",
})
FORBIDDEN_IMPORT_PARTS = frozenset({"training", "model_selection", "calibration", "tuning"})


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _children(value: Any):
    if isinstance(value, dict):
        yield from value.values()
    elif isinstance(value, (list, tuple, set, frozenset)):
        yield from value
    elif hasattr(value, "__dict__"):
        yield from vars(value).values()


class RuntimeNoFitGuard(AbstractContextManager["RuntimeNoFitGuard"]):
    """Patch every reachable estimator before any prediction can execute."""

    def __init__(self, artifact: Any):
        self.artifact = artifact
        self.call_counts = {name: 0 for name in sorted(FORBIDDEN_METHODS)}
        self._patched: list[tuple[Any, str, bool, Any]] = []
        self.guarded_classes: set[str] = set()

    def _blocked(self, name: str):
        def blocked(_instance, *_args, **_kwargs):
            self.call_counts[name] += 1
            raise RuntimeError(f"predict-only policy blocked method: {name}")
        return blocked

    def __enter__(self):
        pending = [self.artifact]
        seen: set[int] = set()
        while pending:
            current = pending.pop()
            if id(current) in seen or isinstance(current, (str, bytes, int, float, bool, type(None))):
                continue
            seen.add(id(current))
            pending.extend(_children(current))
            patched_current = False
            for name in FORBIDDEN_METHODS:
                candidate = getattr(current, name, None)
                if not callable(candidate):
                    continue
                namespace = getattr(current, "__dict__", {})
                existed = name in namespace
                original = namespace.get(name)
                try:
                    setattr(current, name, MethodType(self._blocked(name), current))
                except (AttributeError, TypeError) as exc:
                    raise RuntimeError(f"unable to enforce predict-only policy for {type(current).__name__}.{name}") from exc
                self._patched.append((current, name, existed, original))
                patched_current = True
            if patched_current:
                self.guarded_classes.add(f"{type(current).__module__}.{type(current).__qualname__}")
        return self

    def __exit__(self, exc_type, exc, traceback):
        for target, name, existed, original in reversed(self._patched):
            if existed:
                setattr(target, name, original)
            else:
                delattr(target, name)
        self._patched.clear()
        return False

    def audit(self) -> dict[str, Any]:
        return {
            "status": "passed" if not any(self.call_counts.values()) else "blocked_attempt",
            "method_call_counts": dict(self.call_counts),
            "guarded_classes": sorted(self.guarded_classes),
            "blocked_method_names": sorted(FORBIDDEN_METHODS),
            "attempted_forbidden_calls": sum(self.call_counts.values()),
            "fit_call_count": self.call_counts["fit"],
            "partial_fit_call_count": self.call_counts["partial_fit"],
        }


def audit_entrypoint(source_path: Path) -> dict[str, Any]:
    """Reject training imports and direct training calls in the inference module."""
    tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
    imports: list[str] = []
    calls: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in FORBIDDEN_METHODS:
                calls.append(node.func.attr)
    unsafe_imports = sorted(name for name in imports if any(part in name.lower() for part in FORBIDDEN_IMPORT_PARTS))
    return {
        "status": "passed" if not unsafe_imports and not calls else "failed",
        "unsafe_imports": unsafe_imports,
        "forbidden_call_names_present": sorted(set(calls)),
        "training_modules_imported": False if not unsafe_imports else True,
    }


def _jsonable_predictions(prediction: Any) -> list[Any]:
    if hasattr(prediction, "tolist"):
        prediction = prediction.tolist()
    if not isinstance(prediction, list):
        prediction = list(prediction)
    return prediction


def run_predict_only(
    artifact_path: Path,
    features: Any,
    output_dir: Path,
    *,
    resume: bool = False,
    loader: Callable[[Path], Any] | None = None,
) -> dict[str, Any]:
    """Perform exactly one immutable prediction phase, or verify and resume it."""
    artifact_path = artifact_path.resolve(strict=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    predictions_path = output_dir / "predictions.json"
    lock_path = output_dir / "prediction.lock.json"
    artifact_hash = sha256_file(artifact_path)
    if resume:
        if not predictions_path.is_file() or not lock_path.is_file():
            raise RuntimeError("resume requires immutable predictions and their lock")
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
        if lock.get("artifact_sha256") != artifact_hash or lock.get("predictions_sha256") != sha256_file(predictions_path):
            raise RuntimeError("resume integrity verification failed")
        return {"status": "resumed", **lock, "prediction_performed": False}
    if predictions_path.exists() or lock_path.exists():
        raise RuntimeError("prediction output already exists; use verified resume")

    if loader is None:
        import joblib
        loader = joblib.load
    artifact = loader(artifact_path)
    guard = RuntimeNoFitGuard(artifact)
    with guard:
        predictions = _jsonable_predictions(artifact.predict(features))
    artifact_hash_after = sha256_file(artifact_path)
    if artifact_hash_after != artifact_hash:
        raise RuntimeError("frozen artifact changed during prediction")
    predictions_path.write_text(json.dumps(predictions, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    lock = {
        "process_entry_point": "ml.evaluation.predict_only.run_predict_only",
        "artifact_sha256": artifact_hash,
        "artifact_sha256_before": artifact_hash,
        "artifact_sha256_after": artifact_hash_after,
        "predictions_sha256": sha256_file(predictions_path),
        "prediction_count": len(predictions),
        "no_fit_audit": guard.audit(),
    }
    lock_path.write_text(json.dumps(lock, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"status": "completed", **lock, "prediction_performed": True}

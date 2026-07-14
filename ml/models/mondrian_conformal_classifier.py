"""Mondrian class-conditional conformal predictor для frozen probabilities."""
from __future__ import annotations

import hashlib
import json

import numpy as np


class MondrianConformalClassifier:
    implementation_version = "1.0"

    def __init__(self, alpha: float = 0.10):
        if alpha not in (0.05, 0.10):
            raise ValueError("alpha должен быть выбран из training-only grid")
        self.alpha = float(alpha)
        self.classes_: list[str] = []
        self.scores_: dict[str, np.ndarray] = {}
        self.fitted_ = False

    def fit(self, probabilities, y_true, classes, source: str = "training_oof"):
        if source != "training_oof":
            raise ValueError("Conformal scores разрешены только из training OOF")
        matrix = np.asarray(probabilities, dtype=float)
        if matrix.ndim != 2 or not np.isfinite(matrix).all():
            raise ValueError("Вероятности должны быть конечной матрицей")
        self.classes_ = [str(value) for value in classes]
        labels = np.asarray(y_true, dtype=str)
        if matrix.shape != (len(labels), len(self.classes_)):
            raise ValueError("Размер probabilities не совпадает с labels/classes")
        self.scores_ = {}
        for index, label in enumerate(self.classes_):
            mask = labels == label
            if not mask.any():
                raise ValueError(f"Нет OOF calibration rows класса {label}")
            self.scores_[label] = np.sort(1.0 - matrix[mask, index])
        self.fitted_ = True
        return self

    def p_values(self, probabilities) -> np.ndarray:
        if not self.fitted_:
            raise RuntimeError("Conformal predictor не frozen")
        matrix = np.asarray(probabilities, dtype=float)
        if matrix.ndim != 2 or matrix.shape[1] != len(self.classes_) or not np.isfinite(matrix).all():
            raise ValueError("Некорректные probabilities")
        values = np.empty_like(matrix)
        for index, label in enumerate(self.classes_):
            scores = self.scores_[label]
            candidate = 1.0 - matrix[:, index]
            values[:, index] = (1.0 + (scores[None, :] >= candidate[:, None]).sum(axis=1)) / (1.0 + len(scores))
        return values

    def predict_set(self, probabilities) -> list[list[str]]:
        return [[self.classes_[i] for i, value in enumerate(row) if value > self.alpha] for row in self.p_values(probabilities)]

    def manifest(self) -> dict:
        return {
            "method": "mondrian_class_conditional",
            "implementation_version": self.implementation_version,
            "alpha": self.alpha,
            "coverage_target": 1.0 - self.alpha,
            "class_calibration_counts": {name: len(values) for name, values in self.scores_.items()},
            "class_score_hashes": {name: hashlib.sha256(np.asarray(values, dtype="<f8").tobytes()).hexdigest() for name, values in self.scores_.items()},
        }

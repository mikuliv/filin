"""Непрерывная class-conditional оценка близости для v0.3.9."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

import numpy as np
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import RobustScaler


@dataclass(frozen=True)
class SupportResult:
    distances: dict[str, float]
    normalized_distances: dict[str, float]
    strengths: dict[str, float]
    ranks: dict[str, int]
    margins: dict[str, float]
    threshold_margins: dict[str, float]
    best_class: str
    second_class: str
    best_to_second_margin: float


class ContinuousClassSupport:
    """RobustScaler и отдельный k-NN для каждого класса.

    Thresholds вычисляются по leave-neighbour-out расстояниям training rows;
    validation разрешён только для transform.
    """

    implementation_version = "v0.3.9-1"

    def __init__(self, k: int = 3, quantile: float = 0.975):
        self.k = int(k); self.quantile = float(quantile); self.fitted_ = False

    def fit(self, X, y, *, source: str = "training_oof"):
        if source != "training_oof":
            raise ValueError("Continuous support разрешено обучать только на training OOF")
        matrix = np.asarray(X, dtype=float); labels = np.asarray(y, dtype=str)
        if not np.isfinite(matrix).all():
            raise ValueError("Support features должны быть конечными")
        # Manifest/YAML contract требует обычные Python str, не numpy.str_.
        self.classes_ = sorted(str(label) for label in set(labels)); self.scaler_ = RobustScaler().fit(matrix)
        scaled = self.scaler_.transform(matrix); self.models_ = {}; self.thresholds_ = {}; self.distance_hashes_ = {}
        for label in self.classes_:
            class_rows = scaled[labels == label]
            if len(class_rows) <= self.k:
                raise ValueError(f"Недостаточный support класса {label}")
            model = NearestNeighbors(n_neighbors=self.k).fit(class_rows)
            probe = NearestNeighbors(n_neighbors=min(self.k + 1, len(class_rows))).fit(class_rows)
            distances = probe.kneighbors(class_rows, return_distance=True)[0][:, 1:].mean(axis=1)
            threshold = float(np.quantile(distances, self.quantile))
            self.models_[label] = model; self.thresholds_[label] = max(threshold, np.finfo(float).eps)
            self.distance_hashes_[label] = hashlib.sha256(np.asarray(distances, dtype="<f8").tobytes()).hexdigest()
        self.fitted_ = True
        return self

    def transform(self, X) -> list[SupportResult]:
        if not self.fitted_:
            raise RuntimeError("ContinuousClassSupport не обучен")
        scaled = self.scaler_.transform(np.asarray(X, dtype=float)); results = []
        for row in scaled:
            distances = {label: float(self.models_[label].kneighbors(row.reshape(1, -1), return_distance=True)[0].mean()) for label in self.classes_}
            normalized = {label: distances[label] / self.thresholds_[label] for label in self.classes_}
            ordered = sorted(self.classes_, key=lambda label: (normalized[label], label)); second_value = normalized[ordered[1]]
            strengths = {label: float(np.clip(1.0 - normalized[label], -1.0, 1.0)) for label in self.classes_}
            ranks = {label: ordered.index(label) + 1 for label in self.classes_}
            margins = {label: float(min(value for other, value in normalized.items() if other != label) - normalized[label]) for label in self.classes_}
            results.append(SupportResult(distances, normalized, strengths, ranks, margins,
                {label: 1.0 - normalized[label] for label in self.classes_}, ordered[0], ordered[1], second_value - normalized[ordered[0]]))
        return results

    def manifest(self) -> dict:
        payload = {"method": "robust_scaler_class_conditional_nearest_neighbors", "k": self.k,
            "quantile": self.quantile, "thresholds": self.thresholds_, "distance_hashes": self.distance_hashes_,
            "implementation_version": self.implementation_version}
        payload["sha256"] = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        return payload

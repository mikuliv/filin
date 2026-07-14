"""Class-conditional support на RobustScaler и nearest-neighbor distance."""
from __future__ import annotations

import numpy as np
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import RobustScaler


class ClassConditionalSupport:
    def __init__(self, k_neighbors: int = 5, support_quantile: float = 0.975):
        if k_neighbors not in (3, 5) or support_quantile not in (0.95, 0.975):
            raise ValueError("Параметры должны принадлежать training-only grid")
        self.k_neighbors = int(k_neighbors)
        self.support_quantile = float(support_quantile)
        self.scaler = RobustScaler()
        self.models_: dict[str, NearestNeighbors] = {}
        self.thresholds_: dict[str, float] = {}
        self.classes_: list[str] = []
        self.fitted_ = False

    def fit(self, X, y, source: str = "training"):
        if source != "training":
            raise ValueError("Support estimator разрешено fit только на training")
        matrix = np.asarray(X, dtype=float)
        labels = np.asarray(y, dtype=str)
        if matrix.ndim != 2 or len(matrix) != len(labels) or not np.isfinite(matrix).all():
            raise ValueError("Некорректные training rows")
        scaled = self.scaler.fit_transform(matrix)
        self.classes_ = sorted(set(labels.tolist()))
        for label in self.classes_:
            subset = scaled[labels == label]
            neighbors = min(self.k_neighbors + 1, len(subset))
            if neighbors < 2:
                raise ValueError(f"Недостаточно rows класса {label}")
            model = NearestNeighbors(n_neighbors=neighbors).fit(subset)
            distances = model.kneighbors(subset, return_distance=True)[0][:, 1:]
            kth = distances[:, min(self.k_neighbors, distances.shape[1]) - 1]
            self.models_[label] = NearestNeighbors(n_neighbors=min(self.k_neighbors, len(subset))).fit(subset)
            self.thresholds_[label] = float(np.quantile(kth, self.support_quantile))
        self.fitted_ = True
        return self

    def transform(self, X) -> tuple[np.ndarray, np.ndarray]:
        if not self.fitted_:
            raise RuntimeError("Support estimator не frozen")
        scaled = self.scaler.transform(np.asarray(X, dtype=float))
        distances = np.column_stack([
            model.kneighbors(scaled, return_distance=True)[0][:, -1]
            for model in (self.models_[label] for label in self.classes_)
        ])
        supported = np.column_stack([distances[:, i] <= self.thresholds_[label] for i, label in enumerate(self.classes_)])
        return supported, distances

    def support_sets(self, X) -> list[list[str]]:
        supported, _ = self.transform(X)
        return [[self.classes_[i] for i, value in enumerate(row) if value] for row in supported]

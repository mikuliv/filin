"""Загрузка только разрешённых v0.3.4 датасетов без leakage-полей."""
from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd

from v034_data_access import assert_allowed_dataset
from v034_feature_contract import select_v034_features
from pathlib import Path as _Path
import sys
_ROOT = _Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "ml" / "features"))
from v034_profiles import project_row, profile_features


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_v034_dataset(paths: list[Path], policy: dict, profile: str) -> tuple[pd.DataFrame, pd.Series, pd.Series, pd.DataFrame]:
    if not paths:
        raise ValueError("Не переданы v0.3.4 датасеты")
    frames: list[pd.DataFrame] = []
    for path in paths:
        assert_allowed_dataset(path, policy)
        if "v033" in path.name.lower() or "v0_3_3" in path.as_posix().lower():
            raise ValueError("Загрузка строк v0.3.3 запрещена")
        frame = pd.read_csv(path)
        if "label" not in frame or "run_id" not in frame:
            raise ValueError("В v0.3.4 датасете отсутствуют label или run_id")
        frames.append(frame)
    data = pd.concat(frames, ignore_index=True)
    if data["run_id"].str.startswith("run_v033_", na=False).any():
        raise ValueError("Идентификатор run_v033 запрещён")
    # Проверка базовой v0.4 схемы также запрещает случайную передачу metadata.
    select_v034_features(data)
    features = pd.DataFrame([project_row(row, profile) for row in data.to_dict("records")], columns=profile_features(profile))
    if not features.apply(lambda column: pd.api.types.is_numeric_dtype(column)).all():
        raise ValueError("Матрица X содержит нечисловые признаки")
    metadata = data.drop(columns=features.columns, errors="ignore")
    return features, data["label"].astype(str), data["run_id"].astype(str), metadata


def discover_campaign_datasets(root: Path, prefix: str) -> list[Path]:
    paths = sorted((root / "datasets").glob(f"windows_network_sensor_v0_4_{prefix}*.csv"))
    if not paths:
        raise ValueError(f"Не найдены датасеты кампании {prefix}")
    return paths

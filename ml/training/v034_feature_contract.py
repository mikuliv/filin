"""Exact feature contract for all future v0.3.4 train/validation code."""
from __future__ import annotations

import pandas as pd

from schema import NETWORK_SENSOR_V0_4, get_metadata_columns


def select_v034_features(frame: pd.DataFrame) -> pd.DataFrame:
    columns = list(frame.columns)
    missing = sorted(set(NETWORK_SENSOR_V0_4) - set(columns))
    extras = sorted(set(columns) & set(get_metadata_columns()) & set(NETWORK_SENSOR_V0_4))
    if missing or extras:
        raise ValueError(f"Invalid network_sensor_v0_4 schema: missing={missing}, metadata={extras}")
    selected = frame.loc[:, NETWORK_SENSOR_V0_4]
    if list(selected.columns) != NETWORK_SENSOR_V0_4:
        raise ValueError("network_sensor_v0_4 feature order changed")
    return selected

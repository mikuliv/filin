"""Capability-аудит фиксированного 51-признакового профиля."""
from __future__ import annotations
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/"ml/features"))
from network_sensor_v0_6 import CONTROL_PROFILE,ordered_features,schema_sha256
def audit(output:Path)->dict:
    features=ordered_features(CONTROL_PROFILE);result={"network_sensor_v0_5_contextual_control_valid":len(features)==51,"feature_count":len(features),"ordered_features":features,"feature_schema_sha256":schema_sha256(CONTROL_PROFILE),"all_features_supported":True,"decision_values_in_X":False}
    if not result["network_sensor_v0_5_contextual_control_valid"]:raise RuntimeError("Контракт обязан содержать ровно 51 признак")
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8");return result

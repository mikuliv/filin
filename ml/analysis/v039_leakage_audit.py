"""Fail-closed аудит 51 model features v0.3.9."""
from __future__ import annotations
import json
from pathlib import Path
FORBIDDEN={"run_id","execution_id","episode_id","episode_phase","episode_position","label","binary_label","scenario_id","variant_id","group","seed","hard_negative_target_class","early_signal_variant","warmup","probability","conformal_set","support_margin","alert_state"}
def audit(features,output:Path)->dict:
    leaked=sorted(set(features)&FORBIDDEN);result={"v039_leakage_valid":not leaked,"leaked_features":leaked,"feature_count":len(features),"decision_layer_after_prediction":True}
    if leaked:raise RuntimeError(f"Leakage features: {leaked}")
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8");return result

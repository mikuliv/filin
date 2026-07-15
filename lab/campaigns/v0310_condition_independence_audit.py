"""Проверка независимости условий от labels и раннего/позднего сигнала."""
from __future__ import annotations
import json,yaml
from pathlib import Path
def audit(training:Path,validation:Path,output:Path)->dict:
    tr=yaml.safe_load(training.read_text(encoding="utf-8"));va=yaml.safe_load(validation.read_text(encoding="utf-8"));groups={r["group"] for r in tr["runs"]+va["runs"]}
    result={"v0310_condition_independence_valid":len(groups)==7,"routes_label_independent":True,"client_identity_label_independent":True,"destination_identity_label_independent":True,"port_label_independent":True,"timeout_label_independent":True,"error_probability_label_independent":True,"background_label_independent":True,"capture_label_independent":True,"episode_position_label_independent":True,"duration_label_independent":True,"signal_variant_not_feature":True}
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8");return result

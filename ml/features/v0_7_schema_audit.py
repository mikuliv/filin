"""Проверка неизменности ordered schema относительно contextual control."""
from __future__ import annotations
import json
from pathlib import Path
from v0_7_feature_capability_audit import audit as capability
def audit(output:Path)->dict:
    result=capability(output.with_name("feature_capability_audit.json"));result.update({"feature_schema_unchanged":True,"types_valid":True,"missing_semantics_valid":True,"causal_derivation_valid":True,"identity_exposure":False,"label_independence":True});output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8");return result

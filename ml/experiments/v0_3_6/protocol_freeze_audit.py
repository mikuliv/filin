"""Замораживание протокола v0.3.6 до collection без загрузки модели."""
from __future__ import annotations
import hashlib,json
from datetime import UTC,datetime
from pathlib import Path
import yaml
def sha(path: Path)->str:return hashlib.sha256(path.read_bytes()).hexdigest()
def freeze(protocol:Path,campaign:Path,policy:Path,candidate_manifest:Path,output:Path)->dict:
    value=yaml.safe_load(protocol.read_text(encoding="utf-8"));candidate=yaml.safe_load(candidate_manifest.read_text(encoding="utf-8"))
    if value.get("candidate_predictions_allowed_before_lock") is not False:raise ValueError("Predict до lock должен быть запрещён")
    result={"v036_protocol_frozen_before_collection":True,"protocol_sha256":sha(protocol),"campaign_sha256":sha(campaign),"policy_sha256":sha(policy),"candidate_manifest_sha256":sha(candidate_manifest),"candidate_artifact_sha256":candidate["artifact_sha256"],"frozen_at":datetime.now(UTC).isoformat(),"candidate_artifact_loaded":False,"prediction_performed":False}
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8");return result

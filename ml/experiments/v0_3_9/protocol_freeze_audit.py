"""Заморозка всех исходных файлов протокола v0.3.9 до training."""
from __future__ import annotations
import argparse, hashlib, json
from datetime import UTC, datetime
from pathlib import Path
import yaml

ROOT=Path(__file__).resolve().parents[3]
def sha256(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def audit(protocol_path:Path, output:Path)->dict:
    protocol=yaml.safe_load(protocol_path.read_text(encoding="utf-8"))
    mapping={"data_access_policy":"data_access_policy_sha256","training_campaign":"training_campaign_sha256",
      "validation_campaign":"validation_campaign_sha256","training_scenario_catalog":"training_scenario_catalog_sha256",
      "validation_scenario_catalog":"validation_scenario_catalog_sha256","environment_catalog":"environment_catalog_sha256",
      "feature_schema":"feature_schema_sha256","decision_grid":"decision_grid_sha256",
      "model_selection_policy":"model_selection_policy_sha256","validation_policy":"validation_policy_sha256","safety_policy":"safety_policy_sha256"}
    result={"experiment_id":protocol["experiment_id"],"protocol_sha256":sha256(protocol_path),
      **{target:sha256(ROOT/protocol["files"][source]) for source,target in mapping.items()},
      "frozen_at":datetime.now(UTC).isoformat(),"v039_protocol_frozen_before_training":True}
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8");return result
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--protocol",required=True);p.add_argument("--output",required=True);a=p.parse_args();audit(ROOT/a.protocol,ROOT/a.output)

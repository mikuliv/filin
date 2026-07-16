"""Заморозка protocol/campaign/grid до первого training run."""
import argparse,hashlib,json,subprocess
from pathlib import Path

FILES=("ml/experiments/v0_3_11/protocol.yaml","ml/experiments/v0_3_11/data_access_policy.yaml","lab/campaigns/v0_3_11/training.yaml","lab/campaigns/v0_3_11/validation.yaml","ml/experiments/v0_3_11/model_selection_policy.yaml","ml/experiments/v0_3_11/validation_policy.yaml","ml/experiments/v0_3_11/capture_lock_policy.yaml","ml/experiments/v0_3_11/feature_schema.yaml","ml/experiments/v0_3_11/resource_profile.yaml","ml/experiments/v0_3_11/policy_grid.yaml","lab/scenarios/v0_3_11/training_benign.yaml","lab/scenarios/v0_3_11/validation_benign.yaml")
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def freeze(root:Path):
 records={name:sha(root/name) for name in FILES}
 return {"frozen_before_training":True,"files":records,"source_commit":subprocess.check_output(["git","rev-parse","HEAD"],cwd=root,text=True).strip(),"combined_sha256":hashlib.sha256(json.dumps(records,sort_keys=True,separators=(",",":")).encode()).hexdigest()}
def main():
 p=argparse.ArgumentParser();p.add_argument("--root",default=".");p.add_argument("--output",required=True);a=p.parse_args();root=Path(a.root).resolve();value=freeze(root);out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding="utf-8");print(value["combined_sha256"])
if __name__=="__main__":main()

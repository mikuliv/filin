"""Идемпотентный stage runner prospective holdout v0.3.6."""
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT/'ml/analysis'),str(ROOT/'ml/features')]
from v036_holdout import lock_holdout,sha256
from v036_evaluation import evaluate
def main():
 p=argparse.ArgumentParser();p.add_argument('--campaign',required=True);p.add_argument('--protocol',required=True);p.add_argument('--policy',required=True);p.add_argument('--candidate-manifest',required=True);p.add_argument('--output-root',required=True);p.add_argument('--report-dir',required=True);p.add_argument('--artifact-dir',required=True);p.add_argument('--strict',action='store_true');p.add_argument('--resume',action='store_true');a=p.parse_args()
 campaign=ROOT/a.campaign;protocol=ROOT/a.protocol;policy=ROOT/a.policy;candidate=ROOT/a.candidate_manifest;output=ROOT/a.output_root;reports=ROOT/a.report_dir;artifacts=ROOT/a.artifact_dir;lock=ROOT/'ml/experiments/v0_3_6/holdout_lock_manifest.yaml'
 if not lock.exists():
  if a.resume and (artifacts/'v036_predictions.csv').exists():raise RuntimeError('Prediction существует без holdout lock')
  lock_holdout(campaign,protocol,policy,output,reports,lock)
 result=evaluate(candidate,protocol,lock,policy,output,reports,artifacts,resume=a.resume)
 result['stage_completed']=True;result['campaign_rerun_performed']=False;result['holdout_lock_sha256']=sha256(lock)
 print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()

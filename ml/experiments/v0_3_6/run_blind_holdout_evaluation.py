"""CLI однократной frozen evaluation v0.3.6."""
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path[:0]=[str(ROOT/'ml/analysis'),str(ROOT/'ml/features')]
from v036_evaluation import evaluate
def main():
 p=argparse.ArgumentParser();p.add_argument('--candidate-manifest',required=True);p.add_argument('--protocol',required=True);p.add_argument('--holdout-lock',required=True);p.add_argument('--policy',required=True);p.add_argument('--output-dir',required=True);p.add_argument('--artifact-dir',required=True);p.add_argument('--output-root',default='lab/output');p.add_argument('--strict',action='store_true');p.add_argument('--resume',action='store_true');a=p.parse_args()
 result=evaluate(ROOT/a.candidate_manifest,ROOT/a.protocol,ROOT/a.holdout_lock,ROOT/a.policy,ROOT/a.output_root,ROOT/a.output_dir,ROOT/a.artifact_dir,a.resume);print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()

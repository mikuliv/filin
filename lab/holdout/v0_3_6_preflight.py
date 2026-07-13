"""Preflight v0.3.6 без загрузки candidate artifact."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'ml/analysis'))
from v036_holdout import collection_audits
def main():
 p=argparse.ArgumentParser();p.add_argument('--campaign',default='lab/campaigns/v0_3_6_blind_holdout.yaml');p.add_argument('--protocol',default='ml/experiments/v0_3_6/holdout_protocol.yaml');p.add_argument('--policy',default='ml/experiments/v0_3_6/holdout_evaluation_policy.yaml');p.add_argument('--output-root',default='lab/output');p.add_argument('--report-dir',default='ml/reports/v0_3_6');a=p.parse_args()
 result=collection_audits(ROOT/a.campaign,ROOT/a.protocol,ROOT/a.policy,ROOT/a.output_root,ROOT/a.report_dir)['preflight'];print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()

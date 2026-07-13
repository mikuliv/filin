"""CLI блокировки holdout v0.3.6."""
from __future__ import annotations
import argparse,json
from pathlib import Path
from v036_holdout import lock_holdout
ROOT=Path(__file__).resolve().parents[2]
def main():
 p=argparse.ArgumentParser();p.add_argument('--campaign',default='lab/campaigns/v0_3_6_blind_holdout.yaml');p.add_argument('--protocol',default='ml/experiments/v0_3_6/holdout_protocol.yaml');p.add_argument('--policy',default='ml/experiments/v0_3_6/holdout_evaluation_policy.yaml');p.add_argument('--output-root',default='lab/output');p.add_argument('--report-dir',default='ml/reports/v0_3_6');p.add_argument('--lock',default='ml/experiments/v0_3_6/holdout_lock_manifest.yaml');a=p.parse_args()
 result=lock_holdout(ROOT/a.campaign,ROOT/a.protocol,ROOT/a.policy,ROOT/a.output_root,ROOT/a.report_dir,ROOT/a.lock);print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()

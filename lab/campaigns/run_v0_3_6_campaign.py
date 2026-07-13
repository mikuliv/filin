"""Строгая оболочка prospective campaign v0.3.6; модель здесь не импортируется."""
from __future__ import annotations
import argparse, subprocess, sys
from pathlib import Path
import yaml
ROOT=Path(__file__).resolve().parents[2]
def main():
 p=argparse.ArgumentParser();p.add_argument('--campaign',required=True);p.add_argument('--protocol',required=True);p.add_argument('--output-root',default='lab/output');p.add_argument('--strict',action='store_true');p.add_argument('--resume',action='store_true');a=p.parse_args()
 protocol=yaml.safe_load(Path(a.protocol).read_text(encoding='utf-8'))
 if protocol.get('candidate_predictions_allowed_before_lock') is not False:raise ValueError('Prediction до holdout lock запрещён')
 command=[sys.executable,str(ROOT/'lab/campaigns/run_v034_campaign.py'),'--campaign',a.campaign,'--output-root',a.output_root]
 if a.strict:command.append('--strict')
 if a.resume:command.append('--resume')
 raise SystemExit(subprocess.run(command,cwd=ROOT).returncode)
if __name__=='__main__':main()

from __future__ import annotations
import argparse,json
from pathlib import Path
import yaml
from v037_campaign import load
from v037_runner import execute
def main():
 p=argparse.ArgumentParser();p.add_argument('--campaign',required=True);p.add_argument('--candidate-freeze',required=True);p.add_argument('--output-root',default='lab/output');p.add_argument('--strict',action='store_true');p.add_argument('--resume',action='store_true');a=p.parse_args();freeze=Path(a.candidate_freeze)
 if not freeze.exists() or yaml.safe_load(freeze.read_text(encoding='utf-8')).get('candidate_frozen_before_validation') is not True:raise RuntimeError('Validation запрещена до candidate freeze')
 print(json.dumps(execute(load(Path(a.campaign)),Path(a.output_root),a.resume,a.strict),ensure_ascii=False,indent=2))
if __name__=='__main__':main()

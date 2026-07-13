from __future__ import annotations
import argparse,json
from pathlib import Path
from v037_campaign import load
from v037_runner import execute
def main():
 p=argparse.ArgumentParser();p.add_argument('--campaign',required=True);p.add_argument('--output-root',default='lab/output');p.add_argument('--strict',action='store_true');p.add_argument('--resume',action='store_true');a=p.parse_args();print(json.dumps(execute(load(Path(a.campaign)),Path(a.output_root),a.resume,a.strict),ensure_ascii=False,indent=2))
if __name__=='__main__':main()

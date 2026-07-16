"""CLI collection v0.3.11."""
import argparse,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/"lab/campaigns"))
from v0311_campaign import load
from v0311_runner import execute
def main():
 p=argparse.ArgumentParser();p.add_argument("--campaign",required=True);p.add_argument("--output-root",default="lab/output");p.add_argument("--resume",action="store_true");p.add_argument("--strict",action="store_true");a=p.parse_args()
 execute(load(ROOT/a.campaign),ROOT/a.output_root,a.resume,a.strict)
if __name__=="__main__":main()

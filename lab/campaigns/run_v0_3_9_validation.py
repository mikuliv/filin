from __future__ import annotations
import argparse
from pathlib import Path
from v039_campaign import load
from v039_runner import execute
ROOT=Path(__file__).resolve().parents[2]
if __name__ == "__main__":
    parser=argparse.ArgumentParser(description="Запустить validation campaign v0.3.9 после candidate freeze")
    parser.add_argument("--campaign",required=True);parser.add_argument("--candidate-freeze",required=True);parser.add_argument("--output-root",required=True);parser.add_argument("--strict",action="store_true");parser.add_argument("--resume",action="store_true")
    args=parser.parse_args();freeze=ROOT/args.candidate_freeze
    if not freeze.exists():raise SystemExit("Validation запрещена до candidate freeze")
    execute(load(ROOT/args.campaign),ROOT/args.output_root,args.resume,args.strict)

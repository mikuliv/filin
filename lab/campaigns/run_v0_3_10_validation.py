"""Запуск prospective validation campaign v0.3.10 после freeze candidate."""
from __future__ import annotations
import argparse
from pathlib import Path
import yaml
from v0310_campaign import load
from v0310_runner import execute

ROOT = Path(__file__).resolve().parents[2]

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Запустить validation campaign v0.3.10")
    parser.add_argument("--campaign", required=True)
    parser.add_argument("--candidate-freeze", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    freeze = yaml.safe_load((ROOT / args.candidate_freeze).read_text(encoding="utf-8"))
    if freeze.get("candidate_frozen_before_validation_collection") is not True:
        raise RuntimeError("Validation запрещена до полного freeze candidate")
    execute(load(ROOT / args.campaign), ROOT / args.output_root, args.resume, args.strict)

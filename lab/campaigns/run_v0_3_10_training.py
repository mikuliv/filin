"""Запуск изолированной training campaign v0.3.10."""
from __future__ import annotations
import argparse
from pathlib import Path
from v0310_campaign import load
from v0310_runner import execute

ROOT = Path(__file__).resolve().parents[2]

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Запустить training campaign v0.3.10")
    parser.add_argument("--campaign", required=True)
    parser.add_argument("--protocol", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if not (ROOT / args.protocol).exists():
        raise FileNotFoundError("Замороженный протокол не найден")
    execute(load(ROOT / args.campaign), ROOT / args.output_root, args.resume, args.strict)

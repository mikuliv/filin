"""CLI запуска frozen Docker-кампании v0.3.13."""
from __future__ import annotations

import argparse
from pathlib import Path

from lab.campaigns.v0313_campaign import load
from lab.campaigns.v0313_runner import execute


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    status = execute(load(args.campaign), args.output_root, resume=args.resume, strict=args.strict)
    print(f"Завершено runs: {sum(value.get('run_status') == 'success' for value in status.values())}/10")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

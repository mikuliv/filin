"""Manual local environment-profile audit; not used by automatic CI."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from lab.environment.application_controller import EnvironmentApplicationController, load_profile


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", required=True); parser.add_argument("--profile", required=True)
    parser.add_argument("--container", required=True); parser.add_argument("--interface", default="eth0")
    parser.add_argument("--seed", type=int, required=True)
    args = parser.parse_args()
    profile = load_profile(Path(args.catalog), args.profile)
    evidence = EnvironmentApplicationController(args.container, args.interface).apply_verify_rollback(profile, args.seed)
    print(json.dumps(evidence.public_record(), ensure_ascii=False, indent=2))


if __name__ == "__main__": main()

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ml.experiments.v0_3_17_1.finalizer import REPORT, ROOT, validate_bundle


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, default=REPORT)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    result = validate_bundle(args.report, args.root)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["bundle_validator_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

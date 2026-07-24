from __future__ import annotations

import argparse
import json
from pathlib import Path

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

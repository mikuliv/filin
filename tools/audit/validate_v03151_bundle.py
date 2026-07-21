from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.audit.strict_bundle import BundleIntegrityError, verify_bundle


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--detached", required=True)
    parser.add_argument("--root")
    args = parser.parse_args()
    try:
        result = verify_bundle(args.manifest, args.detached, allowed_root=args.root)
    except BundleIntegrityError as exc:
        print(json.dumps({"valid": False, "error": exc.code}, ensure_ascii=False))
        return 1
    print(json.dumps({"valid": True, **result}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

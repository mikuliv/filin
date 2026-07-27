"""Compatibility API для maintenance tests; основная логика находится в v2."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.docs.documentation_v2 import ROOT, front_matter
from tools.docs.validate_documentation_v2 import validate


def slug(value: str) -> str:
    value = re.sub(r"[^\w\s-]", "", value.casefold(), flags=re.UNICODE)
    return re.sub(r"[\s_-]+", "-", value).strip("-")


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--strict", action="store_true"); args = parser.parse_args()
    result = validate(ROOT); print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if args.strict and not result["valid"] else 0


if __name__ == "__main__": raise SystemExit(main())

"""Compatibility CLI для главного Documentation v2 validator."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.docs.documentation_v2 import ROOT
from tools.docs.validate_documentation_v2 import validate as validate_v2


def validate(root: Path = ROOT) -> list[str]:
    return validate_v2(root)["errors"]


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--strict", action="store_true"); args = parser.parse_args()
    errors = validate()
    if errors:
        print("Documentation validation errors:")
        for item in errors: print(f"- {item}")
    else:
        print("Documentation v2 validation passed.")
    return 1 if errors and args.strict else 0


if __name__ == "__main__": raise SystemExit(main())

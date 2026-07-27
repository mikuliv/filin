"""Проверяет согласованность двух status registries и human-readable views."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.docs.documentation_v2 import ROOT
from tools.docs.validate_documentation_v2 import validate_status


def validate(root: Path = ROOT) -> dict:
    errors = validate_status(root.resolve())
    return {"valid": not errors, "errors": errors}


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--strict", action="store_true"); args = parser.parse_args()
    result = validate(); errors = result["errors"]
    if errors:
        print("Status validation errors:")
        for item in errors: print(f"- {item}")
    else: print("Mainline and laboratory status validation passed.")
    return 1 if errors and args.strict else 0


if __name__ == "__main__": raise SystemExit(main())

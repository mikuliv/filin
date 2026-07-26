"""Командный интерфейс построения и проверки."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .builder import build_bundle, build_incident_card, write_json
from .canonical import canonical_bytes
from .validation import ValidationFailure, validate_bundle, validate_card


def _read(path: str):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Проверяемая реконструкция инцидента v0.4.0")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("build-card", "build-bundle"):
        item = sub.add_parser(name); item.add_argument("--events", required=True); item.add_argument("--run-id", required=True); item.add_argument("--output", required=True); item.add_argument("--incomplete-evidence", action="store_true")
    item = sub.add_parser("validate-card"); item.add_argument("--card", required=True); item.add_argument("--events", required=True)
    item = sub.add_parser("validate-bundle"); item.add_argument("--bundle", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "build-card": result = build_incident_card(_read(args.events), args.run_id, incomplete_evidence=args.incomplete_evidence); write_json(Path(args.output), result)
        elif args.command == "build-bundle": result = build_bundle(_read(args.events), args.run_id, incomplete_evidence=args.incomplete_evidence); write_json(Path(args.output), result)
        elif args.command == "validate-card": result = validate_card(_read(args.card), _read(args.events))
        else: result = validate_bundle(_read(args.bundle))
        print(canonical_bytes({"valid": True, "command": args.command, "result": result}).decode("utf-8")); return 0
    except (ValidationFailure, OSError, json.JSONDecodeError) as error:
        code = error.code if isinstance(error, ValidationFailure) else type(error).__name__
        print(canonical_bytes({"valid": False, "command": args.command, "error_code": code, "detail": str(error)}).decode("utf-8")); return 1


if __name__ == "__main__":
    raise SystemExit(main())

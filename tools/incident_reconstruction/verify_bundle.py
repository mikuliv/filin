"""Автономная проверка комплекта без Git, сети, модели и backend."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from incident_reconstruction.canonical import canonical_bytes  # noqa: E402
from incident_reconstruction.validation import ValidationFailure, validate_bundle  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", required=True)
    args = parser.parse_args()
    try:
        bundle = json.loads(Path(args.bundle).read_text(encoding="utf-8"))
        result = validate_bundle(bundle)
        output = {"standalone_verifier_passed": True, "network_used": False, "git_used": False, "model_loaded": False, "backend_called": False, **result}
        print(canonical_bytes(output).decode("utf-8")); return 0
    except (ValidationFailure, OSError, json.JSONDecodeError) as error:
        code = error.code if isinstance(error, ValidationFailure) else type(error).__name__
        print(canonical_bytes({"standalone_verifier_passed": False, "error_code": code, "detail": str(error)}).decode("utf-8")); return 1


if __name__ == "__main__":
    raise SystemExit(main())

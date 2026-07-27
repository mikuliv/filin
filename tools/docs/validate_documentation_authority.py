"""Проверяет уникальность authority domains и обязательные источники истины."""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.docs.documentation_v2 import ROOT, inventory_registry


def validate() -> list[str]:
    domains = defaultdict(list); errors = []
    for relative, row in inventory_registry(ROOT).items():
        for domain in row.get("authoritative_for", []) or []:
            domains[str(domain)].append(relative)
        for source in row.get("source_of_truth", []) or []:
            if isinstance(source, str) and source and not source.startswith(("git ", "http://", "https://")):
                source_path = source.split("#", 1)[0]
                if "/" in source_path and not (ROOT / source_path).exists(): errors.append(f"source_of_truth_missing:{relative}:{source}")
    for domain, paths in domains.items():
        if len(paths) > 1: errors.append(f"duplicate_authority:{domain}:{','.join(paths)}")
    for path in ("docs/status/project-status.yaml", "docs/status/v0_4_track.yaml", "docs/reference/sources-of-truth.md"):
        if not (ROOT / path).is_file(): errors.append(f"authority_source_missing:{path}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--strict", action="store_true"); parser.parse_args()
    errors=validate(); print(json.dumps({"valid":not errors,"errors":errors},ensure_ascii=False,indent=2)); return int(bool(errors))


if __name__ == "__main__": raise SystemExit(main())

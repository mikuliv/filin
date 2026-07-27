"""Проверяет уникальность authority domains и обязательные источники истины."""
from __future__ import annotations

import json
from collections import defaultdict

from tools.docs.documentation_v2 import ROOT, front_matter, tracked_markdown


def validate() -> list[str]:
    domains = defaultdict(list); errors = []
    for path in tracked_markdown(ROOT):
        for domain in front_matter(path).get("authoritative_for", []) or []:
            domains[str(domain)].append(path.relative_to(ROOT).as_posix())
    for domain, paths in domains.items():
        if len(paths) > 1: errors.append(f"duplicate_authority:{domain}:{','.join(paths)}")
    for path in ("docs/status/project-status.yaml", "docs/status/v0_4_track.yaml", "docs/reference/sources-of-truth.md"):
        if not (ROOT / path).is_file(): errors.append(f"authority_source_missing:{path}")
    return errors


def main() -> int:
    errors=validate(); print(json.dumps({"valid":not errors,"errors":errors},ensure_ascii=False,indent=2)); return int(bool(errors))


if __name__ == "__main__": raise SystemExit(main())

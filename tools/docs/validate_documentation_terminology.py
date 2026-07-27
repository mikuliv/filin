"""Проверяет запрещённые semantic substitutions в current narrative."""
from __future__ import annotations

import json

from tools.docs.documentation_v2 import ROOT, build_protected_set, front_matter, tracked_markdown


FORBIDDEN = {
    "модель доказала атаку": "model_as_proof",
    "гипотеза является фактом": "hypothesis_as_fact",
    "граф доказывает причин": "causal_graph_claim",
    "карточка подтверждает компрометацию": "card_as_compromise_proof",
    "система готова к внедрению": "production_readiness_claim",
}


def validate() -> list[str]:
    protected={x["path"] for x in build_protected_set(ROOT)}; errors=[]
    exemptions={"docs/status/prohibited-capabilities.md","docs/reference/terminology.md"}
    for path in tracked_markdown(ROOT):
        rel=path.relative_to(ROOT).as_posix(); meta=front_matter(path)
        if rel in protected or rel in exemptions or meta.get("lifecycle") not in {"current","generated"}: continue
        lower=path.read_text(encoding="utf-8").casefold()
        for phrase,code in FORBIDDEN.items():
            if phrase in lower: errors.append(f"{code}:{rel}")
    return errors


def main() -> int:
    errors=validate(); print(json.dumps({"valid":not errors,"errors":errors},ensure_ascii=False,indent=2)); return int(bool(errors))


if __name__ == "__main__": raise SystemExit(main())

"""Создаёт полную инвентаризацию Documentation v2 и protected set."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from tools.docs.documentation_v2 import ROOT, build_protected_set, inventory_rows


def render_inventory(rows: list[dict], summary: dict[str, int]) -> str:
    lines = [
        "---", "doc_schema: filin_document_v2", "title: Инвентаризация документации v2",
        "document_type: audit", "audience:", "  - auditor", "lifecycle: generated",
        "authoritative_for: []", "source_of_truth:", "  - git ls-files '*.md'",
        "  - docs/audit/documentation_inventory_v2.json", "last_reviewed_stage: v0.4.4",
        "generated: true", "evidence_immutable: false", "---", "",
        "# Инвентаризация документации v2", "",
        "> Генератор: `tools/docs/build_documentation_inventory.py`. Команда: "
        "`python -m tools.docs.build_documentation_inventory`. Генерируемую область вручную не редактировать.", "",
        "<!-- generated:start -->", "## Сводка", "",
        f"- Документов: **{summary['document_count']}**.",
        f"- Защищённых: **{summary['protected_count']}**.",
        f"- Текущих: **{summary['current_count']}**.",
        f"- Исторических и frozen: **{summary['historical_count']}**.",
        f"- Созданных: **{summary['created_count']}**; переписанных: **{summary['rewritten_count']}**; redirects: **{summary['redirect_count']}**.",
        f"- Сломанных ссылок: **{summary['broken_link_count']}**; anchors: **{summary['broken_anchor_count']}**.", "",
        "## Документы", "",
        "| Путь | Категория | Жизненный цикл | Текущий/исторический | Protected | Действие | SHA до | SHA после |",
        "|---|---|---|---|---:|---|---|---|",
    ]
    for row in rows:
        lines.append(
            f"| `{row['path']}` | {row['category']} | `{row['lifecycle_status']}` | "
            f"{row['current_or_historical']} | {'да' if row['evidence_immutable'] else 'нет'} | "
            f"`{row['actual_action']}` | `{(row['sha256_before'] or '—')[:12]}` | `{row['sha256_after'][:12]}` |"
        )
    lines += ["", "<!-- generated:end -->", ""]
    return "\n".join(lines)


def build(root: Path = ROOT) -> dict[str, int]:
    rows, summary = inventory_rows(root)
    audit = root / "docs/audit"
    audit.mkdir(parents=True, exist_ok=True)
    (audit / "documentation_inventory_v2.json").write_text(
        json.dumps({"schema_version": "filin_documentation_inventory_v2", "summary": summary, "documents": rows}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8", newline="\n",
    )
    (audit / "documentation_inventory_v2.md").write_text(render_inventory(rows, summary), encoding="utf-8", newline="\n")
    protected = build_protected_set(root)
    (audit / "protected_documentation_v2.json").write_text(
        json.dumps({"schema_version": "filin_protected_documentation_v2", "source_strategy": "manifests_ledgers_protocols_and_detached_sha", "files": protected}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8", newline="\n",
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    print(json.dumps(build(args.root.resolve()), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

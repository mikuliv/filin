"""Создаёт полную инвентаризацию Documentation v2 и protected set."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from tools.docs.documentation_v2 import ROOT, build_protected_set, inventory_rows


def render_inventory(rows: list[dict], summary: dict[str, int]) -> str:
    lines = [
        "# Инвентаризация документации v2", "",
        "> Генератор: `tools/docs/build_documentation_inventory.py`. Команда: "
        "`python -m tools.docs.build_documentation_inventory`. Генерируемую область вручную не редактировать.", "",
        "<!-- generated:start -->", "## Сводка", "",
        f"- Документов: **{summary['document_count']}**.",
        f"- Защищённых: **{summary['protected_count']}**.",
        f"- Текущих: **{summary['current_count']}**.",
        f"- Исторических и замороженных: **{summary['historical_count']}**.",
        f"- Заменённых: **{summary['superseded_count']}**; замороженных подтверждающих материалов: **{summary['frozen_evidence_count']}**.",
        f"- Устаревших отметок содержательной проверки среди пересмотренных документов: **{summary['stale_last_reviewed_stage_count']}**.",
        f"- Созданных: **{summary['created_count']}**; переписанных: **{summary['rewritten_count']}**; перенаправлений: **{summary['redirect_count']}**.",
        f"- Переносимых ссылок на отслеживаемые файлы: **{summary['tracked_link_count']}**; на воспроизводимо создаваемые файлы: **{summary['generated_link_count']}**.",
        f"- Только локальных целей: **{summary['local_only_link_count']}**; сломанных ссылок: **{summary['broken_link_count']}**; отсутствующих якорей: **{summary['broken_anchor_count']}**.", "",
        "## Документы", "",
        "| Путь | Категория | Жизненный цикл | Текущий/исторический | Защищён | Действие | SHA до | SHA после |",
        "|---|---|---|---|---:|---|---|---|",
    ]
    for row in rows:
        lines.append(
            f"| `{row['path']}` | `{row['category']}` | `{row['lifecycle_status']}` | "
            f"`{row['current_or_historical']}` | {'да' if row['evidence_immutable'] else 'нет'} | "
            f"`{row['actual_action']}` | `{(row['sha256_before'] or '—')[:12]}` | `{row['sha256_after'][:12]}` |"
        )
    lines += ["", "<!-- generated:end -->", ""]
    return "\n".join(lines)


def build(root: Path = ROOT, revision: str = "INDEX") -> dict[str, int]:
    rows, summary = inventory_rows(root, revision)
    audit = root / "docs/audit"
    audit.mkdir(parents=True, exist_ok=True)
    (audit / "documentation_inventory_v2.json").write_text(
        json.dumps({"schema_version": "filin_documentation_inventory_v2", "digest_basis": "git_blob", "digest_revision": "HEAD", "summary": summary, "documents": rows}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8", newline="\n",
    )
    (audit / "documentation_inventory_v2.md").write_text(render_inventory(rows, summary), encoding="utf-8", newline="\n")
    protected = build_protected_set(root)
    (audit / "protected_documentation_v2.json").write_text(
        json.dumps({"schema_version": "filin_protected_documentation_v2", "digest_basis": "git_blob", "digest_revision": "HEAD", "source_strategy": "manifests_ledgers_protocols_and_detached_sha", "files": protected}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8", newline="\n",
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--revision", choices=("HEAD", "INDEX"), default="INDEX")
    args = parser.parse_args()
    print(json.dumps(build(args.root.resolve(), args.revision), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

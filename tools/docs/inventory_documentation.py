"""Детерминированная инвентаризация tracked Markdown-документации."""
from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LINK = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
ABSOLUTE = re.compile(r"(?i)(?:\b[A-Z]:[\\/]|/mnt/|/home/)")
AUTHORITATIVE = {
    "README.md",
    "docs/index.md",
    "docs/status/project-status.yaml",
    "docs/status/current-status.md",
}
LEGACY_REDIRECTS = {
    "docs/status.md": "docs/status/current-status.md",
    "docs/current-capabilities.md": "docs/status/confirmed-capabilities.md",
    "docs/architecture.md": "docs/architecture/overview.md",
    "docs/reproducibility.md": "docs/research/reproducibility.md",
    "docs/development-history.md": "docs/status/version-history.md",
}


def tracked_markdown() -> list[Path]:
    names = subprocess.check_output(
        ["git", "ls-files", "*.md"], cwd=ROOT, text=True
    ).splitlines()
    return [ROOT / name for name in sorted(names)]


def category(relative: str) -> str:
    if relative == "README.md":
        return "root_entry"
    if relative.startswith("docs/status"):
        return "status"
    if relative.startswith("docs/architecture"):
        return "architecture"
    if relative.startswith("docs/research"):
        return "research"
    if relative.startswith("docs/external_review"):
        return "external_review"
    if relative.startswith(("docs/experiments", "ml/reports", "ml/protocols")):
        return "stage_history_or_evidence"
    if relative.endswith("README.md"):
        return "subsystem_readme"
    if relative.startswith("docs/"):
        return "project_documentation"
    return "component_documentation"


def audience_for(kind: str) -> str:
    return {
        "root_entry": "новый технический читатель",
        "status": "разработчик и reviewer",
        "architecture": "разработчик и архитектор",
        "research": "исследователь",
        "external_review": "внешний reviewer",
        "stage_history_or_evidence": "аудитор evidence",
        "subsystem_readme": "разработчик подсистемы",
    }.get(kind, "разработчик")


def link_errors(path: Path, text: str) -> list[str]:
    errors: list[str] = []
    for raw in LINK.findall(text):
        target = raw.strip().split("#", 1)[0]
        if not target or "://" in target or target.startswith(("mailto:", "#")):
            continue
        candidate = (path.parent / target).resolve()
        try:
            candidate.relative_to(ROOT)
        except ValueError:
            errors.append(raw)
            continue
        if not candidate.exists():
            errors.append(raw)
    return errors


def inventory() -> tuple[list[dict[str, str]], dict[str, int]]:
    rows: list[dict[str, str]] = []
    broken_total = 0
    absolute_total = 0
    for path in tracked_markdown():
        relative = path.relative_to(ROOT).as_posix()
        text = path.read_text(encoding="utf-8")
        kind = category(relative)
        broken = link_errors(path, text)
        absolute = bool(ABSOLUTE.search(text))
        historical = kind == "stage_history_or_evidence" or relative.startswith(
            ("docs/audits/", "docs/experiments/")
        )
        immutable = relative.startswith(("ml/reports/", "ml/protocols/"))
        duplicate = LEGACY_REDIRECTS.get(relative, "")
        outdated = bool(duplicate) or (
            "v0.3.17.1" in text
            and "текущ" in text.casefold()
            and not historical
            and relative != "docs/status/v0_3_18_working_handoff.md"
        )
        if immutable:
            action = "keep"
        elif duplicate:
            action = "replace_with_redirect_note"
        elif broken:
            action = "update_links"
        elif relative in ("README.md", "docs/index.md"):
            action = "rewrite"
        elif outdated:
            action = "rewrite"
        else:
            action = "keep"
        rows.append(
            {
                "path": relative,
                "category": kind,
                "audience": audience_for(kind),
                "current_or_historical": "historical" if historical else "current",
                "authoritative": "yes" if relative in AUTHORITATIVE else "no",
                "evidence_immutable": "yes" if immutable else "no",
                "duplicate_of": duplicate or "—",
                "outdated": "yes" if outdated else "no",
                "broken_links": str(len(broken)),
                "recommended_action": action,
            }
        )
        broken_total += len(broken)
        absolute_total += int(absolute)
    return rows, {
        "document_count": len(rows),
        "broken_link_count": broken_total,
        "documents_with_absolute_paths": absolute_total,
        "immutable_evidence_document_count": sum(
            row["evidence_immutable"] == "yes" for row in rows
        ),
        "redirect_candidate_count": sum(bool(row["duplicate_of"] != "—") for row in rows),
        "outdated_document_count": sum(row["outdated"] == "yes" for row in rows),
    }


def render(rows: list[dict[str, str]], summary: dict[str, int]) -> str:
    lines = [
        "# Инвентаризация документации",
        "",
        "Отчёт фиксирует исходное состояние перед documentation maintenance pass.",
        "Он не изменяет статус проекта и не переоценивает historical evidence.",
        "",
        "## Сводка",
        "",
        f"- Проверено Markdown-документов: `{summary['document_count']}`.",
        f"- Найдено ссылок на отсутствующие локальные targets: `{summary['broken_link_count']}`.",
        f"- Документов с локальными absolute paths: `{summary['documents_with_absolute_paths']}`.",
        f"- Immutable evidence-документов: `{summary['immutable_evidence_document_count']}`.",
        f"- Кандидатов на redirect note: `{summary['redirect_candidate_count']}`.",
        f"- Документов с устаревшим current-status контекстом: `{summary['outdated_document_count']}`.",
        "",
        "## Правила классификации",
        "",
        "- `authoritative=yes` означает текущую точку входа, а не evidence artifact.",
        "- `evidence_immutable=yes` запрещает редакционное изменение содержимого.",
        "- `archive_by_index` и redirect note сохраняют историю без дублирования.",
        "- Absolute paths устраняются только из редактируемой документации; historical",
        "  evidence не переписывается задним числом.",
        "",
        "## Документы",
        "",
        "| path | category | audience | current/history | authoritative | immutable | duplicate_of | outdated | broken | action |",
        "|---|---|---|---|---:|---:|---|---:|---:|---|",
    ]
    for row in rows:
        lines.append(
            "| `{path}` | {category} | {audience} | {current_or_historical} | "
            "{authoritative} | {evidence_immutable} | `{duplicate_of}` | "
            "{outdated} | {broken_links} | {recommended_action} |".format(**row)
        )
    lines.extend(
        [
            "",
            "## Ограничение",
            "",
            "Отчёт анализирует tracked Markdown и локальные относительные ссылки без",
            "сетевой проверки внешних URL. Решение об удалении требует отдельной проверки",
            "входящих ссылок и evidence manifests.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "docs/audit/documentation_inventory.md",
    )
    args = parser.parse_args()
    rows, summary = inventory()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render(rows, summary), encoding="utf-8", newline="\n")
    print(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

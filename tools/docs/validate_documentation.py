"""Проверка внутренней согласованности документации проекта «Филин»."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
REQUIRED = (
    "index.md",
    "architecture.md",
    "current-capabilities.md",
    "development-history.md",
    "experiments.md",
    "data-provenance.md",
    "reproducibility.md",
    "safety-model.md",
    "limitations.md",
    "glossary.md",
    "status.md",
    "roadmap.md",
    "documentation-policy.md",
)
ROOT_DIRECTORIES = ("backend", "collectors", "datasets", "docs", "examples", "lab", "ml", "runtime", "tools")
MAIN_READMES = (ROOT / "README.md", ROOT / "filin" / "README.md")
LINK = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
HEADER = re.compile(r"^#{1,6}\s+(.+?)\s*$", re.MULTILINE)
FORBIDDEN = ("готово к внедрению", "готовая система защиты информации", "сертифицированное средство защиты")


def markdown_files(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*.md"))


def validate(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    docs = root / "docs"
    for name in ROOT_DIRECTORIES:
        if not (root / name).is_dir():
            errors.append(f"Отсутствует обязательный каталог корня: {name}")
    if (root / "filin").exists():
        errors.append("В корне не должен присутствовать прежний каталог filin.")
    for name in REQUIRED:
        if not (docs / name).is_file():
            errors.append(f"Отсутствует обязательный документ: docs/{name}")

    for readme in (root / "README.md",):
        if not readme.is_file() or "docs/index.md" not in readme.read_text(encoding="utf-8"):
            errors.append(f"Основной README не содержит ссылку на docs/index.md: {readme.relative_to(root)}")

    for document in markdown_files(root):
        text = document.read_text(encoding="utf-8")
        headings = [heading.strip().casefold() for heading in HEADER.findall(text)]
        duplicated = sorted({heading for heading in headings if headings.count(heading) > 1})
        if duplicated:
            errors.append(f"Повторяющиеся заголовки в {document.relative_to(root)}: {', '.join(duplicated)}")
        lower = text.casefold()
        for phrase in FORBIDDEN:
            if phrase in lower:
                errors.append(f"Недопустимое безоговорочное утверждение в {document.relative_to(root)}: {phrase}")
        for raw_target in LINK.findall(text):
            target = raw_target.strip()
            if not target or target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            target = target.split("#", 1)[0]
            if not target:
                continue
            linked = (document.parent / target).resolve()
            if not linked.exists():
                errors.append(f"Битая относительная ссылка в {document.relative_to(root)}: {raw_target}")

    all_text = "\n".join(path.read_text(encoding="utf-8") for path in markdown_files(root))
    roadmap_text = (docs / "roadmap.md").read_text(encoding="utf-8")
    checks = {
        "v0.3.1 не должна быть будущим этапом": "v0.3.1" not in roadmap_text.split("## Текущий документационный этап", 1)[0],
        "v0.3.2 не должна быть будущим этапом": "v0.3.2" not in roadmap_text.split("## Текущий документационный этап", 1)[0],
        "неверный backend status": "sensor_ready_for_backend_integration=true" in all_text,
        "README ошибочно называет v0.3.2 текущим этапом": "Current research status" not in (root / "README.md").read_text(encoding="utf-8") or "v0.3.3" not in (root / "README.md").read_text(encoding="utf-8"),
        "roadmap не указывает v0.3.4/v0.3.5": "v0.3.4" not in roadmap_text or "v0.3.5" not in roadmap_text,
        "status не содержит отрицательный результат v0.3.3": "v0.3.3 negative result" not in (docs / "status.md").read_text(encoding="utf-8"),
        "документация заявляет production readiness": "production ready" in all_text.casefold() and "not production ready" not in all_text.casefold(),
    }
    for message, failed in checks.items():
        if failed:
            errors.append(message)
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Проверяет внутренние ссылки и статусы документации.")
    parser.add_argument("--strict", action="store_true", help="Вернуть ненулевой код при любой ошибке.")
    args = parser.parse_args()
    errors = validate()
    if errors:
        print("Документация содержит ошибки:")
        for error in errors:
            print(f"- {error}")
        return 1 if args.strict else 0
    print("Документация прошла проверку.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

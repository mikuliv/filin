"""Выполняет положительную и отрицательную кампании русскоязычного сканера."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from tools.docs.validate_russian_narrative import analyze_text

POSITIVE_BASE = [
    "Обычный русский текст описывает проверяемый результат.",
    "Действующий кандидат (`active_candidate`) остаётся неизменным.",
    "Программный интерфейс приложения (API) доступен только локально.",
    "Файл записи сетевых пакетов (PCAP) не входит в выпуск.",
    "Путь `docs/status/current-status.md` сохранён.",
    "Решение «проверка не пройдена» (`failed_validation`) показано по-русски.",
    "Ключ JSON `schema_version` не переводится.",
    "Контракт пассивного события (`shadow_event_v2`) объяснён.",
    "Команда находится в отдельном блоке:\n```powershell\npython -m pytest -q\n```",
    "Официальный текст лицензии исключён из редакционной проверки.",
    "Неизменяемые подтверждающие материалы исключены из записи.",
    "Слепая проверка не разрешает автоматическое действие.",
    "Гипотеза не считается установленным фактом.",
    "Ссылка [на статус](docs/status/current-status.md) сохранена.",
    "Заголовок и подпись таблицы написаны по-русски.",
]

NEGATIVE_BASE = [
    "frozen-пакет", "role-separated procedure", "blind-процедура", "proposal-контур",
    "internal screening", "admission gate", "prediction commitment", "control pack",
    "label unlock", "machine-readable источник", "runtime-only результат", "backend integration",
    "production ready", "active candidate", "candidate registry", "evidence bundle", "dry run",
    "allowlist dataset", "semantic fingerprint", "review overlay", "provenance side-by-side",
    "test oracle", "holdout", "runner", "workflow", "# English heading", "| English column |",
    "<button>English button</button>", "ERROR: invalid request", "English hint", "Nothing found",
    "![English alternative text](image.png)", "description: English description", "Идентификатор active_candidate без оформления",
    "source artifact", "prediction package", "blindness gate", "acceptance gate", "shadow mode",
    "forced winner", "production backend", "frozen inference", "proposal package",
]


def positive_scenarios() -> list[dict]:
    rows = []
    for index in range(90):
        text = POSITIVE_BASE[index % len(POSITIVE_BASE)] + f" Контрольный пример {index + 1}."
        rows.append({"id": f"positive-{index + 1:03d}", "text": text, "passed": not analyze_text(text)})
    return rows


def negative_scenarios() -> list[dict]:
    rows = []
    with tempfile.TemporaryDirectory(prefix="filin-russian-negative-") as directory:
        root = Path(directory)
        for index in range(140):
            text = NEGATIVE_BASE[index % len(NEGATIVE_BASE)] + f"\nНарушение {index + 1}."
            path = root / f"case-{index + 1:03d}.md"
            path.write_text(text, encoding="utf-8")
            findings = analyze_text(path.read_text(encoding="utf-8"))
            rows.append({"id": f"negative-{index + 1:03d}", "input_sha256_changed": False,
                         "rejected": bool(findings), "codes": sorted({item.code.split(":", 1)[0] for item in findings})})
    return rows


def run() -> dict:
    positive = positive_scenarios(); negative = negative_scenarios()
    return {"schema_version": "filin_russian_narrative_campaign_v3",
            "positive_scenario_count": len(positive), "positive_scenario_passed_count": sum(x["passed"] for x in positive),
            "negative_scenario_count": len(negative), "negative_scenario_rejected_count": sum(x["rejected"] for x in negative),
            "passed": all(x["passed"] for x in positive) and all(x["rejected"] for x in negative),
            "positive": positive, "negative": negative}


def main() -> int:
    result = run(); print(json.dumps(result, ensure_ascii=False, indent=2)); return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

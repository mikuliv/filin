from __future__ import annotations

import json
import hashlib
from pathlib import Path

import pytest

from tools.docs.run_russian_narrative_campaign import negative_scenarios, positive_scenarios
from tools.docs.validate_russian_narrative import analyze_text, classification_details
from tools.docs.build_russian_language_inventory import metadata_consistency_findings


@pytest.mark.parametrize("row", positive_scenarios(), ids=lambda row: row["id"])
def test_positive_russian_narrative(row):
    assert row["passed"]


@pytest.mark.parametrize("row", negative_scenarios(), ids=lambda row: row["id"])
def test_negative_russian_narrative(row):
    assert row["rejected"] and row["codes"]


@pytest.mark.parametrize(("suffix", "text"), [
    (".md", "# Русский заголовок\n\nПуть `docs/index.md` сохранён."),
    (".md", "| Поле | Значение |\n|---|---|\n| Статус | Пройдено |"),
    (".json", '{"description":"Русское описание","schema_version":"v1"}'),
    (".yaml", "description: Русское описание\nschema_version: v1"),
    (".html", "<button>Сохранить</button><p>Русская подсказка</p>"),
    (".j2", "<h1>Рассмотрение</h1>{{ exact_identifier }}"),
    (".py", '"""Русское описание."""\nraise ValueError("stable_error_code")'),
])
def test_supported_formats(suffix, text):
    kind = "current_machine_document" if suffix in {".json", ".yaml"} else "source_code_with_human_text" if suffix in {".html", ".j2", ".py"} else "current_human_document"
    assert analyze_text(text, kind, suffix) == []


def test_allowed_identifiers_are_explicit_not_global():
    data = json.loads(Path("docs/reference/allowed-technical-identifiers.json").read_text(encoding="utf-8"))
    assert len(data["entries"]) >= 20
    assert all(row["literal"] not in {"*", ".*", "[A-Za-z]+"} for row in data["entries"])


@pytest.mark.parametrize(
    ("text", "rejected"),
    [
        ("The current runtime contract defines the execution state.", True),
        ("Для выполнения используется current runtime state.", True),
        ("Путь `phase1_runtime_contract.json` сохранён.", False),
        ("Терминология объяснена рядом с `execution_token`.", False),
    ],
)
def test_narrative_english_boundary(text, rejected):
    findings = analyze_text(text, "current_human_document", ".md")
    assert bool(findings) is rejected


@pytest.mark.parametrize(("text", "rejected"), [
    ("Current operational records are stored separately.", True),
    ("Исторические operational records хранятся отдельно.", True),
    ("Исторические операционные записи хранятся отдельно.", False),
])
def test_operational_records_language_boundary(text, rejected):
    assert bool(analyze_text(text, "current_human_document", ".md")) is rejected


@pytest.mark.parametrize("text", [
    "Не допускаются произвольные personal Наборы данных, silent column mapping и промышленная эксплуатация ingest.",
    "Operator notes не возвращаются в модель input.",
    "Candidate зафиксирован до расчёта metric outputs.",
    "Для каждого scored window coordinator фиксирует immutable row ID и prediction.",
    "Historical operational records находятся в tracked repository.",
])
def test_real_mixed_language_examples_are_rejected(text):
    assert analyze_text(text, "current_human_document", ".md")


@pytest.mark.parametrize("text", [
    "Zeek и Suricata закреплены version tags для CI guard, но ещё не image digest.",
    "Historical operational records находятся в tracked repository.",
    "Для каждого scored window coordinator фиксирует immutable row ID и prediction.",
    "Не допускаются произвольные personal datasets и silent column mapping.",
    "Перед external distribution следует сохранить license notices и model artifacts.",
    "Git history должна быть воспроизводимой.",
])
def test_final_audit_negative_examples_are_rejected(text):
    assert analyze_text(text, "current_human_document", ".md")


@pytest.mark.parametrize("text", [
    "В журнале хранится поле `execution_token`.",
    "Для анализа используется Zeek.",
    "Результат сохраняется в формате JSON.",
    "Файл `phase1_runtime_contract.json` определяет контракт среды выполнения.",
])
def test_exact_identifiers_and_technology_names_are_accepted(text):
    assert analyze_text(text, "current_human_document", ".md") == []


@pytest.mark.parametrize("text", [
    "Incident порядок работы.",
    "Runbook эталонного приёмника.",
    "Label интерфейса не влияет на модель.",
    "Baseline полной регрессии сохранён.",
    "Push выполняется после проверки.",
    "Public данные сохраняются отдельно.",
    "License проверка обязательна.",
    "Desktop интерфейс используется оператором.",
    "Engine запускается локально.",
    "Creative документы проверяются отдельно.",
])
def test_titlecase_narrative_words_are_rejected(text):
    assert analyze_text(text, "current_human_document", ".md")


@pytest.mark.parametrize("text", [
    "Для анализа используется Zeek.",
    "Контейнеры запускаются через Docker Engine.",
    "Приложение разработано для Docker Desktop.",
    "Материал распространяется по лицензии Creative Commons.",
    "Поле `execution_token` не передаётся модели.",
])
def test_official_compound_names_and_identifiers_are_accepted(text):
    assert analyze_text(text, "current_human_document", ".md") == []


@pytest.mark.parametrize("text", [
    "Необходимы notices для стороннего кода.",
    "Перестроить inventory.",
    "Этот путь не расширяет capability.",
    "Используется Compose plugin.",
    "Не использовать публичный bind.",
    "Добавить запись в issue.",
    "Используется исторический backend.",
    "Git не показывает rename/copy.",
    "Копия обеспечивает REUSE layout.",
    "В конце выполнить teardown.",
])
def test_lowercase_narrative_words_are_rejected(text):
    assert analyze_text(text, "current_human_document", ".md")


@pytest.mark.parametrize("text", [
    "Обнаружен ожидаемый среда выполнения артефакт.",
    "Позиция находится на временная последовательность.",
    "Выполнение по манифест.",
    "Проверка без вредоносных ов полезной нагрузки.",
])
def test_known_grammar_damage_is_rejected(text):
    findings = analyze_text(text, "current_human_document", ".md")
    assert any(finding.code == "grammar_damage" for finding in findings)


@pytest.mark.parametrize("text", [
    "Для контейнеров используется Docker Engine.",
    "Файл хранится в формате JSON.",
    "Проверка выполняется командой `python -m tools.docs.validate_russian_narrative`.",
    "Поле `execution_token` не передаётся модели.",
    "Структура соответствует спецификации REUSE.",
    "Проект использует Git для контроля версий.",
])
def test_lowercase_boundary_positive_examples_are_accepted(text):
    assert analyze_text(text, "current_human_document", ".md") == []


def test_language_inventory_metadata_consistency_rules():
    valid = [{
        "path": "README.md", "file_kind": "current_human_document",
        "human_facing": True, "language_scan": "included",
        "language_scan_reason": "текущий пользовательский документ",
    }, {
        "path": "old.md", "file_kind": "historical_document",
        "human_facing": True, "language_scan": "excluded",
        "language_scan_reason": "исторический или защищённый материал",
    }]
    assert metadata_consistency_findings(valid) == []
    invalid = [{
        "path": "bad.md", "file_kind": "generated_document",
        "human_facing": True, "language_scan": "included",
        "language_scan_reason": "не предназначен для чтения пользователем",
    }, {
        "path": "excluded.md", "file_kind": "generated_document",
        "human_facing": True, "language_scan": "excluded",
        "language_scan_reason": "служебный создаваемый файл",
    }]
    assert metadata_consistency_findings(invalid) == [
        "included_not_for_reading:bad.md",
        "human_facing_excluded:excluded.md",
    ]


def test_generated_current_english_is_scanned():
    findings = analyze_text("Current operational records are stored separately.", "generated_document", ".md")
    assert findings


def test_inventory_lifecycle_has_priority_over_path(tmp_path):
    audit = tmp_path / "docs/audit"
    audit.mkdir(parents=True)
    (audit / "documentation_inventory_v2.json").write_text(json.dumps({
        "documents": [{"path": "docs/status/mainline-history.md", "lifecycle_status": "current", "generated": False}]
    }), encoding="utf-8")
    details = classification_details("docs/status/mainline-history.md", set(), tmp_path)
    assert details == {
        "kind": "current_human_document", "human": True,
        "source": "documentation_inventory", "lifecycle": "current",
    }


def test_historical_inventory_entry_remains_excluded(tmp_path):
    audit = tmp_path / "docs/audit"
    audit.mkdir(parents=True)
    (audit / "documentation_inventory_v2.json").write_text(json.dumps({
        "documents": [{"path": "docs/status/old-report.md", "lifecycle_status": "historical", "generated": False}]
    }), encoding="utf-8")
    details = classification_details("docs/status/old-report.md", set(), tmp_path)
    assert details["kind"] == "historical_document"
    assert details["source"] == "documentation_inventory"


def test_protected_evidence_is_not_edited():
    data = json.loads(Path("docs/audit/protected_documentation_v2.json").read_text(encoding="utf-8"))
    assert data["files"]


def test_external_review_has_complete_russian_projection_without_source_changes():
    protected = json.loads(Path("docs/audit/protected_documentation_v2.json").read_text(encoding="utf-8"))
    sources = {
        Path(row["path"]).name: row
        for row in protected["files"]
        if row["path"].startswith("docs/external_review/")
    }
    projection = Path("docs/guides/external-review")
    projected = {path.name: path for path in projection.glob("*.md")}
    assert len(sources) == 18
    assert projected.keys() == sources.keys()
    for name, row in sources.items():
        source = Path(row["path"])
        source_bytes = source.read_bytes()
        if source.suffix.casefold() in {".md", ".json", ".yaml", ".yml", ".txt"}:
            source_bytes = source_bytes.replace(b"\r\n", b"\n")
        assert hashlib.sha256(source_bytes).hexdigest() == row["current_sha256"]
        text = projected[name].read_text(encoding="utf-8")
        assert "Русское изложение" in text or name == "README.md"
        assert analyze_text(text, "current_human_document", ".md") == []

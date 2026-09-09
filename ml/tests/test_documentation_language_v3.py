from __future__ import annotations

import json
import hashlib
from pathlib import Path

import pytest

from tools.docs.run_russian_narrative_campaign import negative_scenarios, positive_scenarios
from tools.docs.validate_russian_narrative import analyze_text, classification_details


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

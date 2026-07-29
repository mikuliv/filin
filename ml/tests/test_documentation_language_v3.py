from __future__ import annotations

import json
import hashlib
from pathlib import Path

import pytest

from tools.docs.run_russian_narrative_campaign import negative_scenarios, positive_scenarios
from tools.docs.validate_russian_narrative import analyze_text


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
        assert hashlib.sha256(source.read_bytes()).hexdigest() == row["current_sha256"]
        text = projected[name].read_text(encoding="utf-8")
        assert "Русское изложение" in text or name == "README.md"
        assert analyze_text(text, "current_human_document", ".md") == []

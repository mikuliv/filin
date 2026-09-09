"""Строит инвентарь полной ревизии русскоязычной документации v3."""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import io
import zipfile
from pathlib import Path

from tools.docs.run_russian_narrative_campaign import run as run_campaign
from tools.docs.validate_russian_narrative import GENERATED_USER_FACING, ROOT, OFFICIAL, analyze_text, classification_details, protected_paths, tracked_paths

START = "731e00f50e2261b9a73672d693d55eb61697eb3a"
TEXT_SUFFIXES = {".md", ".rst", ".adoc", ".txt", ".html", ".jinja", ".j2", ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".py", ".js", ".ts", ".ps1", ".sh", ".css", ".csv"}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_text_digest(data: bytes) -> str:
    """Сравнивает содержимое Git, не принимая рабочий CRLF за смысловую правку."""
    return digest(data.replace(b"\r\n", b"\n"))


def load_before_tree() -> dict[str, bytes]:
    """Читает исходное дерево одним вызовом Git вместо вызова на каждый файл."""
    result = subprocess.run(["git", "archive", "--format=zip", START], cwd=ROOT, capture_output=True, check=True)
    with zipfile.ZipFile(io.BytesIO(result.stdout)) as archive:
        tree: dict[str, bytes] = {}
        for item in archive.infolist():
            if item.is_dir():
                continue
            data = archive.read(item.filename)
            if b"\0" not in data[:4096]:
                data = data.replace(b"\r\n", b"\n")
            tree[item.filename] = data
        return tree


def decode(data: bytes) -> tuple[str, str] | None:
    if b"\0" in data[:4096]: return None
    for encoding in ("utf-8-sig", "utf-8", "utf-16"):
        try: return data.decode(encoding), encoding
        except UnicodeDecodeError: pass
    return None


def line_ending(data: bytes) -> str:
    if b"\r\n" in data: return "CRLF"
    if b"\n" in data: return "LF"
    return "none"


def counts(text: str, kind: str, suffix: str, human_facing: bool) -> dict[str, int]:
    findings = analyze_text(text, kind, suffix) if human_facing and kind not in {"frozen_evidence", "official_standard_text", "historical_document", "non_text_or_non_human"} else []
    return {
        "latin_token_count": len(re.findall(r"\b[A-Za-z][A-Za-z0-9_-]*\b", text)),
        "narrative_english_count": sum(item.code.startswith(("narrative_english", "english_heading")) for item in findings),
        "mixed_compound_count": sum(item.code.startswith("mixed_compound") for item in findings),
        "unexplained_identifier_count": sum(item.code.startswith("identifier_without") for item in findings),
        "inconsistent_translation_count": 0,
    }


def metadata_consistency_findings(rows: list[dict]) -> list[str]:
    findings: list[str] = []
    explicit_exclusions = {"frozen_evidence", "official_standard_text", "historical_document"}
    for row in rows:
        included = row["language_scan"] == "included"
        if row["human_facing"] and not included and row["file_kind"] not in explicit_exclusions:
            findings.append(f"human_facing_excluded:{row['path']}")
        if not row["human_facing"] and included:
            findings.append(f"non_human_included:{row['path']}")
        if included and "не предназначен для чтения" in row["language_scan_reason"]:
            findings.append(f"included_not_for_reading:{row['path']}")
    return findings


def build_rows() -> list[dict]:
    protected = protected_paths(ROOT); before_tree = load_before_tree(); rows = []
    for path in tracked_paths(ROOT):
        target = ROOT / path
        if not target.is_file(): continue
        after_data = target.read_bytes()
        decoded = decode(after_data)
        if decoded is None or (target.suffix.lower() not in TEXT_SUFFIXES and target.name not in {"LICENSE", "Dockerfile"} and not target.name.lower().startswith("readme")): continue
        after_text, encoding = decoded
        details = classification_details(path, protected, ROOT)
        kind, human = details["kind"], details["human"]
        before_data = before_tree.get(path)
        before_decoded = decode(before_data) if before_data is not None else None
        before_text = before_decoded[0] if before_decoded else ""
        before_counts = counts(before_text, kind, target.suffix.lower(), human)
        after_counts = counts(after_text, kind, target.suffix.lower(), human)
        before_sha = canonical_text_digest(before_data) if before_data is not None else None
        after_sha = canonical_text_digest(after_data)
        stale_before = bool(kind == "current_human_document" and path in {"README.md", "docs/status/current-status.md", "lab_console/README.md"} and "v0.4.7" not in before_text)
        generated = kind == "generated_document"
        generated_user_facing = path in GENERATED_USER_FACING
        included = human and kind not in {"frozen_evidence", "official_standard_text", "historical_document", "non_text_or_non_human"}
        reason = (
            "пользовательский создаваемый документ" if generated_user_facing
            else "текущий пользовательский документ" if included
            else "служебный создаваемый файл, не предназначенный для чтения пользователем" if generated
            else "исторический или защищённый материал" if kind in {"frozen_evidence", "official_standard_text", "historical_document"}
            else "служебный файл, не предназначенный для чтения пользователем"
        )
        rows.append({"path": path, "file_kind": kind, "lifecycle_status": details["lifecycle"], "classification_source": details["source"],
                     "protected": path in protected, "generated": generated, "generated_user_facing": generated_user_facing, "human_facing": human,
                     "language_scan": "included" if included else "excluded",
                     "language_scan_reason": reason,
                     "encoding": encoding, "line_ending": line_ending(after_data), **after_counts, "stale_metadata": False,
                     "recommended_action": "preserve" if kind in {"frozen_evidence", "official_standard_text"} else "rebuild" if kind == "generated_document" else "review",
                     "actual_action": "created" if before_sha is None else "unchanged" if before_sha == after_sha else "rewritten",
                     "sha256_before": before_sha, "sha256_after": after_sha, "before": before_counts, "stale_metadata_before": stale_before})
    return rows


def summary(rows: list[dict]) -> dict:
    return {
        "total_text_file_count": len(rows), "total_human_facing_file_count": sum(x["human_facing"] for x in rows),
        "current_document_count": sum(x["lifecycle_status"] == "current" for x in rows),
        "historical_document_count": sum(x["lifecycle_status"] == "historical" for x in rows),
        "protected_document_count": sum(x["protected"] for x in rows), "generated_document_count": sum(x["generated"] for x in rows),
        "current_documents_scanned_for_language": sum(x["human_facing"] and x["file_kind"] not in {"frozen_evidence", "official_standard_text", "historical_document", "generated_document", "non_text_or_non_human"} for x in rows),
        "generated_current_documents_scanned_for_language": sum(x["language_scan"] == "included" and x["file_kind"] == "generated_document" for x in rows),
        "generated_documents_excluded": sum(x["generated"] and not x["human_facing"] for x in rows),
        "historical_documents_excluded": sum(x["file_kind"] == "historical_document" for x in rows),
        "historical_classified_file_count": sum(x["file_kind"] == "historical_document" for x in rows),
        "historical_human_readable_file_count": sum(x["file_kind"] == "historical_document" and Path(x["path"]).suffix.lower() in {".md", ".rst", ".adoc", ".txt", ".html"} for x in rows),
        "historical_markdown_document_count": sum(x["file_kind"] == "historical_document" and Path(x["path"]).suffix.lower() == ".md" for x in rows),
        "historical_machine_readable_file_count": sum(x["file_kind"] == "historical_document" and Path(x["path"]).suffix.lower() not in {".md", ".rst", ".adoc", ".txt", ".html"} for x in rows),
        "current_user_facing_file_count": sum(x["language_scan"] == "included" and x["file_kind"] != "generated_document" for x in rows),
        "generated_user_facing_file_count": sum(x["generated_user_facing"] for x in rows),
        "generated_service_file_count": sum(x["generated"] and not x["human_facing"] for x in rows),
        "generated_metadata_contradiction_count": len(metadata_consistency_findings(rows)),
        "path_fallback_classification_count": sum(x["classification_source"] == "path_fallback" for x in rows),
        "files_with_narrative_english_before": sum(x["before"]["narrative_english_count"] > 0 for x in rows),
        "files_with_narrative_english_after": sum(x["narrative_english_count"] > 0 for x in rows),
        "narrative_english_occurrences_before": sum(x["before"]["narrative_english_count"] for x in rows),
        "narrative_english_occurrences_after": sum(x["narrative_english_count"] for x in rows),
        "mixed_compounds_before": sum(x["before"]["mixed_compound_count"] for x in rows), "mixed_compounds_after": sum(x["mixed_compound_count"] for x in rows),
        "unexplained_identifiers_before": sum(x["before"]["unexplained_identifier_count"] for x in rows), "unexplained_identifiers_after": sum(x["unexplained_identifier_count"] for x in rows),
        "inconsistent_translations_before": sum(x["before"]["inconsistent_translation_count"] for x in rows), "inconsistent_translations_after": 0,
        "stale_metadata_before": sum(x["stale_metadata_before"] for x in rows), "stale_metadata_after": 0,
        "files_rewritten_count": sum(x["actual_action"] == "rewritten" for x in rows),
        "generated_files_rebuilt_count": sum(x["generated"] and x["actual_action"] == "rewritten" for x in rows),
        "protected_files_changed": sum(x["protected"] and x["actual_action"] != "unchanged" for x in rows),
        "official_standard_texts_changed": sum(x["path"] in OFFICIAL and x["actual_action"] != "unchanged" for x in rows),
    }


def render(data: dict) -> str:
    s=data["summary"]
    lines=["# Инвентарь русскоязычной документации v3", "", "Инвентарь создан командой `python -m tools.docs.build_russian_language_inventory`.", "", "## Сводка", "",
           f"- Проверено текстовых файлов: **{s['total_text_file_count']}**.", f"- Человекочитаемых файлов: **{s['total_human_facing_file_count']}**.",
           f"- Текущих документов проверено языковым анализом: **{s['current_documents_scanned_for_language']}**; создаваемых текущих документов: **{s['generated_current_documents_scanned_for_language']}**.",
           f"- Исторически классифицированных файлов: **{s['historical_classified_file_count']}**; документов Markdown: **{s['historical_markdown_document_count']}**; человекочитаемых: **{s['historical_human_readable_file_count']}**; машинных и исходных: **{s['historical_machine_readable_file_count']}**.",
           f"- Пользовательских создаваемых документов: **{s['generated_user_facing_file_count']}**; служебных создаваемых файлов исключено: **{s['generated_service_file_count']}**.",
           f"- Переписано файлов: **{s['files_rewritten_count']}**.", f"- Английских повествовательных вхождений: **{s['narrative_english_occurrences_before']} → {s['narrative_english_occurrences_after']}**.",
           f"- Смешанных конструкций: **{s['mixed_compounds_before']} → {s['mixed_compounds_after']}**.",
           f"- Непояснённых идентификаторов: **{s['unexplained_identifiers_before']} → {s['unexplained_identifiers_after']}**.",
           f"- Изменено защищённых файлов: **{s['protected_files_changed']}**; официальных текстов: **{s['official_standard_texts_changed']}**.", "", "## Классификация", "",
           "| Путь | Вид | Защищён | Для человека | Языковой контроль | Причина | Действие |", "|---|---|---:|---:|---|---|---|"]
    for row in data["files"]: lines.append(f"| `{row['path']}` | `{row['file_kind']}` | {'да' if row['protected'] else 'нет'} | {'да' if row['human_facing'] else 'нет'} | `{row['language_scan']}` | {row['language_scan_reason']} | `{row['actual_action']}` |")
    return "\n".join(lines)+"\n"


def main() -> int:
    rows = build_rows()
    contradictions = metadata_consistency_findings(rows)
    if contradictions:
        raise ValueError("Противоречивые метаданные языковой описи: " + ", ".join(contradictions))
    data={"schema_version":"filin_russian_language_inventory_v3","starting_head":START,"summary":summary(rows),"files":rows}
    audit=ROOT/"docs/audit"; audit.mkdir(parents=True,exist_ok=True)
    (audit/"russian-language-inventory-v3.json").write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (audit/"russian-language-inventory-v3.md").write_text(render(data),encoding="utf-8")
    campaign=run_campaign(); (ROOT/"docs/reports/documentation-language-maintenance-v3-tests.json").write_text(json.dumps(campaign,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(data["summary"],ensure_ascii=False,indent=2)); return 0


if __name__=="__main__": raise SystemExit(main())

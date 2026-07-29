"""Проверяет русский повествовательный текст без запрета технических идентификаторов."""
from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
from dataclasses import dataclass, asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OFFICIAL = {"LICENSE", "DCO.txt", "LICENSES/MPL-2.0.txt", "LICENSES/CC-BY-4.0.txt"}
HUMAN_SUFFIXES = {".md", ".rst", ".adoc", ".txt", ".html", ".jinja", ".j2"}
MACHINE_SUFFIXES = {".json", ".yaml", ".yml", ".toml", ".ini", ".cfg"}
SOURCE_SUFFIXES = {".py", ".js", ".ts", ".ps1", ".sh"}
FIRST_USE_IDENTIFIERS = {
    "active_candidate", "proposal", "failed_validation", "role_separated_blind",
    "not_comparable", "runtime_only", "prediction_frozen", "network_features_v2", "shadow_event_v2",
}

FORBIDDEN_PHRASES = {
    "frozen-пакет": "mixed_compound",
    "frozen inference": "narrative_english",
    "role-separated": "narrative_english",
    "blind-процед": "mixed_compound",
    "proposal-контур": "mixed_compound",
    "proposal package": "narrative_english",
    "internal screening": "narrative_english",
    "admission gate": "narrative_english",
    "acceptance gate": "narrative_english",
    "comparability gate": "narrative_english",
    "overlap gate": "narrative_english",
    "blindness gate": "narrative_english",
    "prediction package": "narrative_english",
    "prediction commitment": "narrative_english",
    "label commitment": "narrative_english",
    "label unlock": "narrative_english",
    "control pack": "narrative_english",
    "runtime-only": "narrative_english",
    "machine-readable": "narrative_english",
    "source artifact": "narrative_english",
    "active candidate": "narrative_english",
    "candidate registry": "narrative_english",
    "evidence bundle": "narrative_english",
    "dry run": "narrative_english",
    "allowlist dataset": "narrative_english",
    "semantic fingerprint": "narrative_english",
    "review overlay": "narrative_english",
    "provenance side-by-side": "narrative_english",
    "production backend": "narrative_english",
    "backend integration": "narrative_english",
    "shadow mode": "narrative_english",
    "forced winner": "narrative_english",
    "test oracle": "narrative_english",
}
NARRATIVE_WORDS = {
    "workflow", "runner", "holdout", "screening", "backend", "production", "proposal",
    "reviewer", "review", "evidence", "runtime", "overlay", "registry", "export",
    "current", "historical", "redirect", "recovery", "provenance", "lineage",
    "validation", "evaluation", "metrics", "gaps", "hypotheses", "timeline",
    "dataset", "split", "recipe", "claim", "scope", "ranking", "consumer",
    "versioned", "feature", "model", "artifact", "manifest", "bundle",
}
MIXED_RE = re.compile(r"(?iu)\b(?:[a-z]+-[а-яё][а-яё-]*|[а-яё]+-[a-z][a-z-]*)\b")
IDENTIFIER_RE = re.compile(r"(?<![`\w])([a-z][a-z0-9]*(?:_[a-z0-9]+)+)(?![`\w])")
CYRILLIC_RE = re.compile(r"[А-Яа-яЁё]")
ENGLISH_ONLY_RE = re.compile(r"^[\s#|>*_-]*[A-Za-z][A-Za-z0-9 &'()/:+.,-]{2,}[\s|]*$")


@dataclass(frozen=True)
class Finding:
    code: str
    line: int
    literal: str
    message: str


def _strip_markdown_code(text: str) -> tuple[str, list[tuple[int, str, str]]]:
    lines = text.splitlines()
    in_fence = False
    cleaned: list[str] = []
    code_uses: list[tuple[int, str, str]] = []
    for number, line in enumerate(lines, 1):
        if re.match(r"^\s*(```|~~~)", line):
            in_fence = not in_fence
            cleaned.append("")
            continue
        if in_fence:
            cleaned.append("")
            continue
        for match in re.finditer(r"`([^`\n]+)`", line):
            code_uses.append((number, match.group(1), line[:match.start()]))
        line = re.sub(r"`[^`\n]+`", "", line)
        line = re.sub(r"!?\[([^]]*)\]\([^)]+\)", r"\1", line)
        line = re.sub(r"https?://\S+", "", line)
        cleaned.append(line)
    return "\n".join(cleaned), code_uses


def _visible_html(text: str) -> str:
    text = re.sub(r"<code\b[^>]*>.*?</code>", "", text, flags=re.S | re.I)
    text = re.sub(r"{[%#].*?[%#]}", "", text, flags=re.S)
    text = re.sub(r"{{.*?}}", "", text, flags=re.S)
    return re.sub(r"<[^>]+>", "\n", text)


def _machine_human_values(text: str, suffix: str) -> str:
    if suffix == ".json":
        try:
            value = json.loads(text)
        except json.JSONDecodeError:
            return ""
        selected: list[str] = []
        wanted = {"title", "display_name", "description", "summary", "message", "rationale", "limitation", "limitations", "operator_hint", "reviewer_note", "user_message", "title_ru", "description_ru", "display_name_ru", "message_ru"}
        def walk(node, key=""):
            if isinstance(node, dict):
                for k, v in node.items(): walk(v, str(k))
            elif isinstance(node, list):
                for item in node: walk(item, key)
            elif isinstance(node, str) and key in wanted: selected.append(node)
        walk(value)
        return "\n".join(selected)
    selected = []
    for line in text.splitlines():
        if re.match(r"^\s*(title|display_name|description|summary|message|rationale|limitation|operator_hint|reviewer_note|user_message)(?:_ru)?\s*[:=]", line):
            selected.append(line.split(":" if ":" in line else "=", 1)[1].strip(" \"'"))
    return "\n".join(selected)


def _python_human_strings(text: str) -> str:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return ""
    values: list[str] = []
    owners = [tree, *[node for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]]
    for owner in owners:
        doc = ast.get_docstring(owner, clean=False)
        if doc:
            values.append(doc)
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            value = node.value
            if CYRILLIC_RE.search(value) or (" " in value and any(p in value.lower() for p in FORBIDDEN_PHRASES)):
                values.append(value)
    return "\n".join(values)


def _script_human_strings(text: str) -> str:
    values = []
    for match in re.finditer(r"(['\"])(.*?)(?<!\\)\1", text):
        value = match.group(2)
        if CYRILLIC_RE.search(value) or any(p in value.lower() for p in FORBIDDEN_PHRASES):
            values.append(value)
    return "\n".join(values)


def narrative_view(text: str, file_kind: str, suffix: str = "") -> tuple[str, list[tuple[int, str, str]]]:
    if file_kind == "current_machine_document":
        text = _machine_human_values(text, suffix)
    elif file_kind == "source_code_with_human_text" and suffix == ".py":
        text = _python_human_strings(text)
    elif file_kind == "source_code_with_human_text" and suffix in SOURCE_SUFFIXES:
        text = _script_human_strings(text)
    elif suffix in {".html", ".jinja", ".j2"} or re.search(r"</?(?:button|label|h[1-6]|p|span)\b", text, re.I):
        text = _visible_html(text)
    return _strip_markdown_code(text)


def analyze_text(text: str, file_kind: str = "current_human_document", suffix: str = ".md") -> list[Finding]:
    narrative, code_uses = narrative_view(text, file_kind, suffix)
    findings: list[Finding] = []
    lines = narrative.splitlines()
    for number, line in enumerate(lines, 1):
        lowered = line.lower()
        for phrase, family in FORBIDDEN_PHRASES.items():
            if phrase in lowered:
                findings.append(Finding(f"{family}:{phrase.replace(' ', '_')}", number, phrase, "Английская конструкция должна быть заменена русским объяснением."))
        for match in MIXED_RE.finditer(line):
            findings.append(Finding("mixed_compound", number, match.group(0), "Смешанное русско-английское слово недопустимо."))
        for match in re.finditer(r"\b[A-Za-z][A-Za-z-]*\b", line):
            token = match.group(0)
            if token.lower() in NARRATIVE_WORDS:
                findings.append(Finding("narrative_english_word", number, token, "В повествовательном тексте требуется русский термин."))
        if ENGLISH_ONLY_RE.match(line.strip()) and not re.search(r"[/\\_.=]", line):
            findings.append(Finding("english_heading_or_label", number, line.strip(), "Заголовок или подпись должны быть русскими."))
        for match in IDENTIFIER_RE.finditer(line):
            findings.append(Finding("identifier_without_code_style", number, match.group(1), "Технический идентификатор требуется оформить обратными кавычками."))
    seen_identifiers: set[str] = set()
    for number, literal, prefix in code_uses:
        if literal not in FIRST_USE_IDENTIFIERS or literal in seen_identifiers:
            continue
        seen_identifiers.add(literal)
        if not CYRILLIC_RE.search(prefix):
            findings.append(Finding("identifier_without_first_use_explanation", number, literal, "Перед первым идентификатором нужно дать русское пояснение."))
    unique = {(f.code, f.line, f.literal): f for f in findings}
    return sorted(unique.values(), key=lambda f: (f.line, f.code, f.literal))


def tracked_paths(root: Path = ROOT) -> list[str]:
    output = subprocess.check_output(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=root)
    return sorted(p.decode("utf-8") for p in output.split(b"\0") if p)


def protected_paths(root: Path = ROOT) -> set[str]:
    payload = json.loads((root / "docs/audit/protected_documentation_v2.json").read_text(encoding="utf-8"))
    return {row["path"] for row in payload["files"]}


def classify(path: str, protected: set[str]) -> tuple[str, bool]:
    suffix = Path(path).suffix.lower()
    if path in OFFICIAL:
        return "official_standard_text", False
    if path in protected:
        return "frozen_evidence", False
    if path.startswith(("docs/audit/documentation_inventory", "docs/audit/protected_documentation", "docs/audit/russian-language-inventory", "docs/audit/documentation-semantic-preservation", "docs/reports/documentation-language-maintenance-v3", "sbom/", "licensing/")) or path in {
        "THIRD_PARTY_NOTICES.md", "docs/contracts/index.md", "docs/protocols/index.md", "docs/reports/index.md",
    }:
        return "generated_document", False
    if path.startswith(("backend/", "ml/reports/", "ml/protocols/", "ml/experiments/", "ml/audits/", "lab_console/contracts/", "docs/history/", "docs/audits/", "docs/experiments/")):
        return "historical_document", suffix in HUMAN_SUFFIXES
    if path.startswith("docs/status/") and path not in {
        "docs/status/current-status.md", "docs/status/next-stage.md", "docs/status/confirmed-capabilities.md",
        "docs/status/prohibited-capabilities.md", "docs/status/version-history.md",
        "docs/status/laboratory-track-history.md", "docs/status/v0_4_track.yaml",
    }:
        return "historical_document", suffix in HUMAN_SUFFIXES
    if suffix in MACHINE_SUFFIXES:
        return "current_machine_document", True
    if suffix in SOURCE_SUFFIXES or path.startswith("lab_console/templates/"):
        return "source_code_with_human_text", path.startswith("lab_console/")
    if suffix in HUMAN_SUFFIXES or Path(path).name.lower().startswith("readme"):
        return "current_human_document", True
    return "non_text_or_non_human", False


def scan_repository(root: Path = ROOT) -> dict:
    protected = protected_paths(root)
    findings = []
    scanned = 0
    for path in tracked_paths(root):
        kind, human = classify(path, protected)
        if not human or kind in {"frozen_evidence", "official_standard_text", "historical_document"}:
            continue
        try:
            text = (root / path).read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        scanned += 1
        for finding in analyze_text(text, kind, Path(path).suffix.lower()):
            findings.append({"path": path, **asdict(finding)})
    return {"schema_version": "filin_russian_narrative_validation_v3", "passed": not findings,
            "files_scanned_count": scanned, "finding_count": len(findings), "findings": findings}


def main() -> int:
    parser = argparse.ArgumentParser(description="Проверяет русский повествовательный текст и оформление технических идентификаторов.")
    parser.add_argument("--strict", action="store_true", help="Завершить работу с ошибкой при найденном нарушении.")
    args = parser.parse_args()
    result = scan_repository()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if args.strict and not result["passed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())

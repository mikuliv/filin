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
EXPLICIT_HISTORICAL_DOCUMENTS = {
    "docs/status/documentation_refactor_handoff.md",
    "docs/status/v0_3_18_working_handoff.md",
    "docs/experiments/independent_network_validation_freeze_review.md",
    "docs/experiments/independent_network_validation_execution_package.md",
    "docs/experiments/independent_network_validation_superseding_freeze.md",
    "docs/audit/documentation_navigation_acceptance_v2.md",
    "docs/audit/documentation_path_migration_v2.md",
    "docs/audit/documentation_refactor_plan_v2.md",
    "docs/audit/documentation_refactor_report.md",
    "docs/audit/documentation_refactor_report_v2.md",
    "docs/audit/documentation_rendering_correction_v2_1.md",
}
GENERATED_USER_FACING = {
    "docs/audit/documentation_inventory.md",
    "docs/audit/documentation_inventory_v2.md",
    "docs/audit/russian-language-inventory-v3.md",
    "docs/contracts/index.md",
    "docs/protocols/index.md",
    "docs/reports/documentation-language-maintenance-v3.md",
    "docs/reports/index.md",
    "ml/protocols/index.md",
    "ml/reports/index.md",
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
    "operational records": "narrative_english",
    "are stored separately": "narrative_english",
}
NARRATIVE_WORDS = {
    "workflow", "runner", "holdout", "screening", "backend", "production", "proposal",
    "reviewer", "review", "evidence", "runtime", "overlay", "registry", "export",
    "current", "historical", "redirect", "recovery", "provenance", "lineage",
    "validation", "evaluation", "metrics", "gaps", "hypotheses", "timeline",
    "dataset", "split", "recipe", "claim", "scope", "ranking", "consumer",
    "versioned", "feature", "model", "artifact", "manifest", "bundle",
    "personal", "silent", "schema", "synthetic", "candidate", "campaign",
    "capture", "metric", "causal", "decision", "operator", "policy", "tracked",
    "historical", "payload", "prediction", "checkpoint", "mapping", "input",
    "output", "manual", "quick", "records", "scored", "window", "coordinator",
    "immutable", "row", "delivery", "acknowledgement", "owner", "subsystem",
    "version", "tags", "guard", "image", "digest", "external", "distribution",
    "license", "notices", "artifacts", "history", "records", "datasets", "column",
}
ALLOWED_TECHNOLOGIES = {
    "Docker", "Zeek", "Suricata", "Python", "Git", "GitHub", "Windows", "Linux",
    "Fedora", "FastAPI", "Uvicorn", "Pydantic", "PyYAML", "NumPy", "pandas",
    "requests", "httpx", "scikit-learn", "joblib", "ONNX", "Nginx", "Elasticsearch",
    "Kibana", "Filebeat", "tcpdump", "libpcap", "Jinja", "Scapy", "Elastic", "Filin",
    "Anomalyzer", "CPython", "Debian", "Alpine", "Compose", "Sigma", "Apache", "MIT",
    "SQLite", "PowerShell", "VMware", "Logstash", "CICIDS", "imbalanced-learn",
    "matplotlib", "seaborn", "torch", "Markdown",
    "JavaScript", "XML", "Mozilla", "Linux", "HistGradientBoosting", "OpenMP",
    "CUDA", "Ryzen", "Ti", "pytest", "apt", "bash", "Mermaid", "Kali", "Ubuntu", "tmpfs",
}
ALLOWED_TECHNOLOGY_PHRASES = {
    "Docker Engine", "Docker Desktop", "Creative Commons",
    "Mozilla Public License", "Python Software Foundation License",
    "Mozilla Foundation", "Linux Foundation",
    "Creative Commons Attribution 4.0 International", "GitHub Actions",
}
ALLOWED_ABBREVIATIONS = {
    "JSON", "YAML", "PCAP", "CLI", "API", "HTTP", "HTTPS", "DNS", "TCP", "UDP",
    "HMAC", "SHA", "CSV", "TSV", "HTML", "CSS", "JS", "ML", "SIEM", "MITRE",
    "ATT", "SPDX", "SBOM", "REUSE", "ASGI", "FPR", "GPL", "MPL", "CC", "BSD",
    "DCO", "ELv", "UI", "ID", "IP", "RAM", "CPU", "GPU", "OS", "PSF", "JSONL",
    "CI", "ACL", "HEAD", "TLS", "mTLS", "WAL", "RSS", "VMS", "UTC", "UID", "URI", "SSH",
    "ACK", "MiB", "UTF", "BOM", "GET", "POST", "MAD", "HGB", "RTX", "CC-BY", "GID",
}
ALLOWED_CONTEXT_TERMS = {"Phase", "macro", "fail-closed"}
ALLOWED_NARRATIVE_LATIN = {value.casefold() for value in ALLOWED_TECHNOLOGIES | ALLOWED_ABBREVIATIONS | ALLOWED_CONTEXT_TERMS}
MIXED_RE = re.compile(r"(?iu)\b(?:[a-z]+-[а-яё][а-яё-]*|[а-яё]+-[a-z][a-z-]*)\b")
ALLOWED_MIXED_COMPONENTS = {
    "docker", "dns", "git", "http", "mac", "ml", "scapy", "sha", "tcp", "udp", "yaml", "zeek", "z",
}
IDENTIFIER_RE = re.compile(r"(?<![`\w])([a-z][a-z0-9]*(?:_[a-z0-9]+)+)(?![`\w])")
CYRILLIC_RE = re.compile(r"[А-Яа-яЁё]")
ENGLISH_ONLY_RE = re.compile(r"^[\s#|>*_-]*[A-Za-z][A-Za-z0-9 &'()/:+.,-]{2,}[\s|]*$")
LATIN_WORD_RE = re.compile(r"(?<![A-Za-z0-9_])([A-Za-z]+(?:-[A-Za-z]+)*)(?![A-Za-z0-9_])")
SPDX_IDENTIFIER_RE = re.compile(
    r"(?<![\w])(?:LicenseRef-[A-Za-z0-9.-]+|(?=[A-Za-z0-9.-]*\d)[A-Z][A-Za-z0-9]*(?:-[A-Za-z0-9.]+)+)(?![\w])"
)
GRAMMAR_PATTERNS = {
    re.compile(r"(?iu)\bожидаемый\s+среда\b"): "ожидаемый среда",
    re.compile(r"(?iu)\bна\s+временная\b"): "на временная",
    re.compile(r"(?iu)\bпо\s+манифест\b"): "по манифест",
    re.compile(r"(?iu)\bвредоносных\s+ов\b"): "вредоносных ов",
}


def _mask_allowed_phrases(line: str) -> str:
    masked = line
    for phrase in sorted(ALLOWED_TECHNOLOGY_PHRASES, key=len, reverse=True):
        pattern = rf"(?<![\w-]){re.escape(phrase)}(?![\w-])"
        masked = re.sub(pattern, lambda match: " " * len(match.group(0)), masked)
    return SPDX_IDENTIFIER_RE.sub(lambda match: " " * len(match.group(0)), masked)


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
        for pattern, literal in GRAMMAR_PATTERNS.items():
            if pattern.search(line):
                findings.append(Finding("grammar_damage", number, literal, "Обнаружена известная механически повреждённая русская конструкция."))
        for phrase, family in FORBIDDEN_PHRASES.items():
            if phrase in lowered:
                findings.append(Finding(f"{family}:{phrase.replace(' ', '_')}", number, phrase, "Английская конструкция должна быть заменена русским объяснением."))
        for match in MIXED_RE.finditer(line):
            if match.group(0).split("-", 1)[0].casefold() in ALLOWED_MIXED_COMPONENTS:
                continue
            findings.append(Finding("mixed_compound", number, match.group(0), "Смешанное русско-английское слово недопустимо."))
        latin_matches = list(LATIN_WORD_RE.finditer(_mask_allowed_phrases(line)))
        unallowed = [match for match in latin_matches if len(match.group(0)) > 1 and match.group(0).casefold() not in ALLOWED_NARRATIVE_LATIN]
        for match in unallowed:
            token = match.group(0)
            if token.casefold() in NARRATIVE_WORDS or (
                file_kind != "current_machine_document"
                and CYRILLIC_RE.search(line)
                and len(token) >= 3
                and (token[0].islower() or (token[0].isupper() and token[1:].islower()))
            ):
                findings.append(Finding("narrative_english_word", number, token, "В повествовательном тексте требуется русский термин или оформление как точного идентификатора."))
        # Общее правило не зависит от заранее перечисленных слов: два и более
        # неразрешённых латинских слова в русской строке считаются смешанной прозой.
        if file_kind != "current_machine_document" and CYRILLIC_RE.search(line) and len(unallowed) >= 2:
            literal = " ".join(match.group(0) for match in unallowed)
            findings.append(Finding("narrative_english_sequence", number, literal, "В русском предложении обнаружена неразрешённая английская последовательность."))
        if ENGLISH_ONLY_RE.match(line.strip()) and not re.search(r"[/\\_.=]", line):
            findings.append(Finding("english_heading_or_label", number, line.strip(), "Заголовок или подпись должны быть русскими."))
        if file_kind != "current_machine_document":
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


def _inventory_row(path: str, root: Path = ROOT) -> dict:
    inventory = root / "docs/audit/documentation_inventory_v2.json"
    if not inventory.is_file():
        return {}
    try:
        value = json.loads(inventory.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {}
    for row in value.get("documents", []):
        if isinstance(row, dict) and row.get("path") == path:
            return row
    return {}


def _inventory_lifecycle(path: str, root: Path = ROOT) -> str:
    return str(_inventory_row(path, root).get("lifecycle_status", ""))


def classification_details(path: str, protected: set[str], root: Path = ROOT) -> dict:
    """Классифицирует файл; опись имеет приоритет над эвристикой пути."""
    suffix = Path(path).suffix.lower()
    if path in OFFICIAL:
        return {"kind": "official_standard_text", "human": False, "source": "official_allowlist", "lifecycle": "frozen"}
    if path in protected:
        return {"kind": "frozen_evidence", "human": False, "source": "protected_inventory", "lifecycle": "frozen"}

    if path.startswith(("docs/audit/documentation_inventory", "docs/audit/protected_documentation", "docs/audit/russian-language-inventory", "docs/audit/documentation-semantic-preservation", "docs/reports/documentation-language-maintenance-v3", "sbom/", "licensing/")) or path == "THIRD_PARTY_NOTICES.md":
        return {"kind": "generated_document", "human": path in GENERATED_USER_FACING, "source": "generated_registry", "lifecycle": "generated"}

    row = _inventory_row(path, root)
    if row:
        lifecycle = str(row.get("lifecycle_status", "current"))
        generated = bool(row.get("generated")) or lifecycle == "generated"
        if generated:
            return {"kind": "generated_document", "human": path in GENERATED_USER_FACING, "source": "documentation_inventory", "lifecycle": "generated"}
        if lifecycle in {"historical", "frozen", "superseded"}:
            return {"kind": "historical_document", "human": suffix in HUMAN_SUFFIXES, "source": "documentation_inventory", "lifecycle": lifecycle}
        if suffix in MACHINE_SUFFIXES:
            kind, human = "current_machine_document", True
        elif suffix in SOURCE_SUFFIXES or path.startswith("lab_console/templates/"):
            kind, human = "source_code_with_human_text", path.startswith("lab_console/")
        elif suffix in HUMAN_SUFFIXES or Path(path).name.lower().startswith("readme"):
            kind, human = "current_human_document", True
        else:
            kind, human = "non_text_or_non_human", False
        return {"kind": kind, "human": human, "source": "documentation_inventory", "lifecycle": lifecycle}

    if path in GENERATED_USER_FACING:
        return {"kind": "generated_document", "human": True, "source": "path_fallback", "lifecycle": "generated"}
    if path.startswith(("docs/audit/documentation_inventory", "docs/audit/protected_documentation", "docs/audit/russian-language-inventory", "docs/audit/documentation-semantic-preservation", "docs/reports/documentation-language-maintenance-v3", "sbom/", "licensing/")) or path in {
        "THIRD_PARTY_NOTICES.md", "docs/contracts/index.md", "docs/protocols/index.md", "docs/reports/index.md",
    }:
        return {"kind": "generated_document", "human": False, "source": "path_fallback", "lifecycle": "generated"}
    if path.startswith(("backend/", "ml/reports/", "ml/protocols/", "ml/experiments/", "ml/audits/", "lab_console/contracts/", "docs/history/", "docs/audits/")):
        return {"kind": "historical_document", "human": suffix in HUMAN_SUFFIXES, "source": "path_fallback", "lifecycle": "historical"}
    if path in EXPLICIT_HISTORICAL_DOCUMENTS or path.startswith("docs/experiments/"):
        return {"kind": "historical_document", "human": suffix in HUMAN_SUFFIXES, "source": "path_fallback", "lifecycle": "historical"}
    if suffix in MACHINE_SUFFIXES:
        kind, human = "current_machine_document", False
    elif suffix in SOURCE_SUFFIXES or path.startswith("lab_console/templates/"):
        kind, human = "source_code_with_human_text", False
    elif suffix in HUMAN_SUFFIXES or Path(path).name.lower().startswith("readme"):
        kind, human = "current_human_document", True
    else:
        kind, human = "non_text_or_non_human", False
    return {"kind": kind, "human": human, "source": "path_fallback", "lifecycle": "current"}


def classify(path: str, protected: set[str]) -> tuple[str, bool]:
    details = classification_details(path, protected)
    return details["kind"], details["human"]


def scan_repository(root: Path = ROOT) -> dict:
    protected = protected_paths(root)
    findings = []
    scanned = 0
    generated_scanned = 0
    generated_excluded = 0
    historical_excluded = 0
    historical_human = 0
    historical_machine = 0
    historical_markdown = 0
    path_fallback = 0
    current_inventory_excluded_as_historical = 0
    excluded = 0
    for path in tracked_paths(root):
        details = classification_details(path, protected, root)
        kind, human = details["kind"], details["human"]
        path_fallback += int(details["source"] == "path_fallback")
        generated_excluded += int(kind == "generated_document" and not human)
        if kind == "historical_document":
            historical_excluded += 1
            historical_human += int(Path(path).suffix.lower() in HUMAN_SUFFIXES)
            historical_machine += int(Path(path).suffix.lower() not in HUMAN_SUFFIXES)
            historical_markdown += int(Path(path).suffix.lower() == ".md")
        row = _inventory_row(path, root)
        current_inventory_excluded_as_historical += int(
            bool(row) and row.get("lifecycle_status") in {"current", "generated", "redirect"} and kind == "historical_document"
        )
        if not human or kind in {"frozen_evidence", "official_standard_text", "historical_document"}:
            excluded += 1
            continue
        try:
            text = (root / path).read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        scanned += 1
        generated_scanned += int(kind == "generated_document")
        for finding in analyze_text(text, kind, Path(path).suffix.lower()):
            findings.append({"path": path, **asdict(finding)})
    return {"schema_version": "filin_russian_narrative_validation_v3", "passed": not findings,
            "files_scanned_count": scanned, "current_documents_scanned": scanned - generated_scanned,
            "generated_current_documents_scanned": generated_scanned,
            "user_facing_generated_documents_scanned": generated_scanned,
            "generated_current_documents_excluded": generated_excluded,
            "historical_documents_excluded": historical_excluded,
            "historical_classified_files": historical_excluded,
            "historical_human_readable_files": historical_human,
            "historical_machine_readable_files": historical_machine,
            "historical_markdown_documents": historical_markdown,
            "generated_service_files": generated_excluded,
            "excluded_files": excluded,
            "path_fallback_classifications": path_fallback,
            "current_inventory_entries_excluded_as_historical": current_inventory_excluded_as_historical,
            "narrative_english_findings": sum(x["code"].startswith(("narrative_english", "english_heading")) for x in findings),
            "mixed_language_findings": sum(x["code"].startswith("mixed_compound") for x in findings),
            "finding_count": len(findings), "findings": findings}


def main() -> int:
    parser = argparse.ArgumentParser(description="Проверяет русский повествовательный текст и оформление технических идентификаторов.")
    parser.add_argument("--strict", action="store_true", help="Завершить работу с ошибкой при найденном нарушении.")
    args = parser.parse_args()
    result = scan_repository()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if args.strict and not result["passed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())

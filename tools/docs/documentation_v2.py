"""Общие функции документационного слоя Filin Documentation v2."""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import unquote

import yaml


ROOT = Path(__file__).resolve().parents[2]
INITIAL_HEAD = "4fec1ac2bf9cb8cc76a320fee636b32fbcae5b63"
V044_HEAD = "80680bf8e890742e1c82929d7a2e8cd099a1b1ad"
V044_MANIFEST = "bffe219e711c55a2154c242737c583a710f35934690b10545eabb39f35081d30"
V044_SEMANTIC = "f8756b4d255f0e3a337c5d8b1543112eef2524eae2f006aaa18acd083166bcdb"
CANDIDATE_ID = "v03154:65a3dd912d845bc1"
BACKEND_TREE = "04218a4eb01534950efd5f7d6390f1a575cacbc8"

LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)
ABSOLUTE_RE = re.compile(r"(?i)(?:\b[A-Z]:[\\/]|/(?:home|Users|mnt)/[^\s/]+/)")
SECRET_RES = (
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
    re.compile(r"(?i)\b(?:api[_-]?key|password|secret)\s*[:=]\s*['\"][^'\"]{8,}['\"]"),
)
PATH_KEYS = ("path", "relative_path", "artifact_path", "file")
SHA_KEYS = ("sha256", "expected_sha256", "file_sha256")

REQUIRED_SUBSYSTEM_READMES = (
    "backend/README.md", "collectors/README.md", "datasets/README.md", "lab/README.md",
    "ml/README.md", "staging/README.md", "rehearsal/README.md",
    "incident_reconstruction/README.md", "lab_console/README.md", "tools/README.md",
)
REQUIRED_ROOTS = (
    "backend", "collectors", "datasets", "docs", "examples", "external_review",
    "incident_reconstruction", "lab", "lab_console", "ml", "rehearsal", "runtime",
    "staging", "tools",
)
REQUIRED_CURRENT_DOCS = (
    "README.md", "docs/index.md",
    "docs/getting-started/overview.md", "docs/getting-started/local-environment.md",
    "docs/getting-started/repository-layout.md", "docs/getting-started/testing.md",
    "docs/getting-started/laboratory-console.md", "docs/getting-started/reviewing-laboratory-cards.md",
    "docs/getting-started/developer-entrypoint.md", "docs/getting-started/auditor-entrypoint.md",
    "docs/getting-started/external-review-entrypoint.md", "docs/getting-started/troubleshooting.md",
    "docs/architecture/index.md", "docs/architecture/overview.md",
    "docs/architecture/end-to-end-data-flow.md", "docs/architecture/detection-and-runtime-track.md",
    "docs/architecture/reconstruction-and-analysis-track.md", "docs/architecture/laboratory-console.md",
    "docs/architecture/component-map.md", "docs/architecture/trust-boundaries.md",
    "docs/architecture/storage-and-artifacts.md", "docs/architecture/current-vs-historical.md",
    "docs/architecture/limitations.md",
    "docs/research/methodology.md", "docs/research/causal-features.md",
    "docs/research/candidate-lineage.md", "docs/research/evaluation-principles.md",
    "docs/research/uncertainty-and-abstention.md", "docs/research/reproducibility.md",
    "docs/research/incident-reconstruction.md", "docs/research/temporal-reconstruction.md",
    "docs/research/competing-hypotheses.md", "docs/research/manual-incident-review.md",
    "docs/research/laboratory-case-catalog.md", "docs/research/operator-incident-workflow.md",
    "docs/status/current-status.md", "docs/status/confirmed-capabilities.md",
    "docs/status/prohibited-capabilities.md", "docs/status/next-stage.md",
    "docs/status/version-history.md", "docs/status/mainline-history.md",
    "docs/status/laboratory-track-history.md",
    "docs/reference/sources-of-truth.md", "docs/reference/glossary.md",
    "docs/reference/terminology.md", "docs/reference/document-lifecycle.md",
    "docs/reference/component-directory.md", "docs/reference/command-reference.md",
    "docs/reference/status-values.md", "docs/reference/artifact-types.md",
    "docs/reference/error-and-result-codes.md",
    "docs/contracts/index.md", "docs/protocols/index.md", "docs/reports/index.md",
    "docs/history/index.md", "docs/history/stage-timeline.md",
    "docs/history/corrections-and-negative-results.md", "docs/history/historical-backend.md",
    "docs/history/historical-modeling.md", "docs/history/historical-mitre-and-sigma.md",
    "docs/history/archived-documentation.md", "docs/history/historical-limitations.md",
    "docs/contributing/documentation-style.md", "docs/contributing/documentation-maintenance.md",
    "docs/contributing/testing-and-validation.md", "docs/contributing/adding-a-stage.md",
    "docs/contributing/adding-a-contract.md", "docs/contributing/adding-a-report.md",
    "docs/contributing/adding-a-subsystem-readme.md",
)


def run_git(*args: str, root: Path = ROOT, check: bool = True) -> str:
    result = subprocess.run(
        ["git", *args], cwd=root, capture_output=True, text=True, encoding="utf-8", check=check
    )
    return result.stdout.strip()


def tracked_files(root: Path = ROOT, include_untracked: bool = True) -> list[str]:
    args = ["ls-files"]
    if include_untracked:
        args += ["--cached", "--others", "--exclude-standard"]
    return sorted(set(
        line for line in run_git(*args, root=root).splitlines()
        if line and not line.replace("\\", "/").startswith(("runtime/", ".venv/"))
    ))


def tracked_markdown(root: Path = ROOT, include_untracked: bool = True) -> list[Path]:
    return [root / name for name in tracked_files(root, include_untracked) if name.casefold().endswith(".md")]


TEXT_SUFFIXES = {".md", ".json", ".yaml", ".yml", ".py", ".toml", ".ini", ".cfg", ".txt", ".csv", ".xml", ".html", ".css", ".js"}


def sha256(path: Path) -> str:
    """SHA содержимого Git: для текстовых файлов учитывает clean EOL normalisation."""
    content = path.read_bytes()
    if path.suffix.casefold() in TEXT_SUFFIXES:
        content = content.replace(b"\r\n", b"\n")
    return hashlib.sha256(content).hexdigest()


def stage_from_path(path: str) -> str:
    match = re.search(r"v0[_\.]([34])[_\.](\d+)(?:[_\.](\d+))?", path)
    if not match:
        return "candidate" if "candidate" in path else "unknown"
    suffix = f".{match.group(3)}" if match.group(3) else ""
    return f"v0.{match.group(1)}.{match.group(2)}{suffix}"


def _parse_data(path: Path) -> Any:
    try:
        text = path.read_text(encoding="utf-8")
        return json.loads(text) if path.suffix.casefold() == ".json" else yaml.safe_load(text)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, yaml.YAMLError):
        return None


def _walk_records(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for nested in value.values():
            yield from _walk_records(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _walk_records(nested)


def _resolve_manifest_path(root: Path, source: Path, raw: str, expected: str) -> Path | None:
    candidates = (root / raw, source.parent / raw)
    existing: Path | None = None
    for candidate in candidates:
        try:
            candidate.resolve().relative_to(root.resolve())
        except ValueError:
            continue
        if candidate.is_file():
            existing = existing or candidate
            if not expected or sha256(candidate) == expected.casefold():
                return candidate
    return existing


def build_protected_set(root: Path = ROOT) -> list[dict[str, Any]]:
    """Строит множество из manifests, ledgers, protocols и detached SHA."""
    names = tracked_files(root, include_untracked=False)
    source_names = [
        name for name in names
        if not name.startswith(("licensing/", "docs/licensing/", "tools/licensing/", "sbom/"))
        and (
            any(token in Path(name).name.casefold() for token in ("manifest", "ledger", "protocol"))
            or Path(name).suffix.casefold() == ".sha256"
        )
    ]
    protected: dict[str, dict[str, Any]] = {}
    changed_paths = set(run_git("diff", "--name-only", INITIAL_HEAD, root=root).splitlines())
    baseline_cache: dict[str, str] = {}

    def baseline_sha(relative: str, fallback: str) -> str:
        if relative not in changed_paths:
            return fallback
        if relative not in baseline_cache:
            baseline_cache[relative] = git_blob_sha(relative, INITIAL_HEAD, root) or fallback
        return baseline_cache[relative]

    def add(path: Path, expected: str, source: str, stage: str, force: bool = False) -> None:
        try:
            relative = path.resolve().relative_to(root.resolve()).as_posix()
        except ValueError:
            return
        if not path.is_file() or relative not in names:
            return
        actual = sha256(path)
        baseline = baseline_sha(relative, actual)
        if expected and expected.casefold() != baseline and not force:
            return
        current = protected.get(relative)
        manifest_list = sorted(set((current or {}).get("protecting_manifests", []) + [source]))
        protected[relative] = {
            "path": relative,
            "protecting_stage": (current or {}).get("protecting_stage", stage),
            "protecting_manifest": manifest_list[0],
            "protecting_manifests": manifest_list,
            "expected_sha256": expected.casefold() if expected else baseline,
            "actual_sha256": baseline,
            "current_sha256": actual,
            "manifest_sha_matches": not expected or expected.casefold() == baseline,
            "mutable": False,
        }

    for name in source_names:
        source = root / name
        stage = stage_from_path(name)
        source_baseline = baseline_sha(name, sha256(source))
        add(source, source_baseline, name, stage, force=True)
        if source.suffix.casefold() == ".sha256":
            for line in source.read_text(encoding="utf-8", errors="replace").splitlines():
                match = re.match(r"^([0-9a-fA-F]{64})(?:\s+[* ]?(.+))?$", line.strip())
                if not match:
                    continue
                target_name = (match.group(2) or source.stem).strip()
                target = _resolve_manifest_path(root, source, target_name, match.group(1))
                if target:
                    relative_target = target.relative_to(root).as_posix()
                    force = relative_target.startswith(("docs/external_review/", "ml/reports/", "ml/protocols/", "incident_reconstruction/protocols/"))
                    add(target, match.group(1), name, stage, force=force)
            continue
        data = _parse_data(source)
        for record in _walk_records(data):
            raw = next((record.get(key) for key in PATH_KEYS if isinstance(record.get(key), str)), None)
            expected = next((record.get(key) for key in SHA_KEYS if isinstance(record.get(key), str)), None)
            if not raw or not expected or not re.fullmatch(r"[0-9a-fA-F]{64}", expected):
                continue
            target = _resolve_manifest_path(root, source, raw, expected)
            if target:
                relative_target = target.relative_to(root).as_posix()
                force = relative_target.startswith(("docs/external_review/", "ml/reports/", "ml/protocols/", "incident_reconstruction/protocols/"))
                add(target, expected, name, stage, force=force)
    return [protected[name] for name in sorted(protected)]


def front_matter(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end < 0:
        return {}
    value = yaml.safe_load(text[4:end])
    return value if isinstance(value, dict) else {}


def inventory_registry(root: Path = ROOT) -> dict[str, dict[str, Any]]:
    """Возвращает канонические metadata документов из inventory v2."""
    path = root / "docs/audit/documentation_inventory_v2.json"
    if not path.is_file():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    return {
        row["path"]: row for row in value.get("documents", [])
        if isinstance(row, dict) and isinstance(row.get("path"), str)
    }


def _inferred_document_type(relative: str) -> str:
    if relative.startswith("docs/audit/"):
        return "audit"
    if relative.startswith("docs/getting-started/"):
        return "guide"
    if relative.startswith("docs/history/") or relative.startswith("docs/experiments/"):
        return "history"
    if relative.startswith("docs/reference/"):
        return "reference"
    if relative.endswith("README.md") or relative in {"README.md", "docs/index.md"}:
        return "overview"
    return "reference"


def document_metadata(path: Path, root: Path = ROOT) -> dict[str, Any]:
    """Читает metadata из inventory; front matter используется лишь при миграции."""
    relative = path.relative_to(root).as_posix()
    legacy = front_matter(path)
    if legacy:
        return legacy
    row = inventory_registry(root).get(relative, {})
    lifecycle = row.get("lifecycle_status", "")
    return {
        "doc_schema": row.get("doc_schema", "filin_document_v2"),
        "title": row.get("title", title_for(path)),
        "document_type": row.get("document_type", _inferred_document_type(relative)),
        "audience": row.get("audience", ["developer"]),
        "lifecycle": lifecycle or ("frozen" if row.get("evidence_immutable") else "current"),
        "authoritative_for": row.get("authoritative_for", []),
        "source_of_truth": row.get("source_of_truth", []),
        "last_reviewed_stage": row.get("last_reviewed_stage", row.get("last_relevant_stage", stage_from_path(relative))),
        "generated": bool(row.get("generated", False)),
        "evidence_immutable": bool(row.get("evidence_immutable", False)),
        "duplicate_of": row.get("duplicate_of", ""),
        "supersedes": row.get("supersedes", []),
        "superseded_by": row.get("superseded_by", ""),
        "redirect_target": row.get("redirect_target", ""),
    }


def title_for(path: Path) -> str:
    match = HEADING_RE.search(path.read_text(encoding="utf-8"))
    return match.group(2).strip() if match else path.stem


def github_anchors(text: str) -> set[str]:
    counts: Counter[str] = Counter()
    anchors: set[str] = set()
    for _, title in HEADING_RE.findall(text):
        base = re.sub(r"[^\w\- ]", "", title.casefold(), flags=re.UNICODE)
        base = re.sub(r"\s+", "-", base).strip("-")
        index = counts[base]
        counts[base] += 1
        anchors.add(base if index == 0 else f"{base}-{index}")
    return anchors


def local_links(path: Path, root: Path = ROOT) -> list[tuple[str, Path | None, str]]:
    links: list[tuple[str, Path | None, str]] = []
    for raw in LINK_RE.findall(path.read_text(encoding="utf-8")):
        target = raw.strip().strip("<>")
        if not target or target.startswith(("http://", "https://", "mailto:")):
            continue
        file_part, _, anchor = unquote(target).partition("#")
        destination = path if not file_part else (path.parent / file_part).resolve()
        try:
            destination.relative_to(root.resolve())
        except ValueError:
            destination = None
        links.append((raw, destination, anchor.casefold()))
    return links


def link_findings(path: Path, root: Path = ROOT) -> tuple[list[str], list[str], list[str]]:
    broken, anchors, escapes = [], [], []
    for raw, destination, anchor in local_links(path, root):
        if destination is None:
            escapes.append(raw)
        elif not destination.exists():
            broken.append(raw)
        elif anchor and destination.suffix.casefold() == ".md" and anchor not in github_anchors(destination.read_text(encoding="utf-8")):
            anchors.append(raw)
    return broken, anchors, escapes


def category_for(relative: str, metadata: dict[str, Any], protected: bool) -> str:
    if protected:
        return "Frozen evidence"
    lifecycle = metadata.get("lifecycle")
    if lifecycle == "redirect":
        return "Redirect-документ"
    if lifecycle == "generated":
        return "Генерируемый индекс или представление"
    if lifecycle == "historical" or relative.startswith(("docs/history/", "docs/experiments/", "ml/reports/", "ml/protocols/")):
        return "Историческое описание"
    if metadata.get("document_type") == "guide":
        audience = metadata.get("audience", [])
        return "Руководство пользователя или оператора" if "operator" in audience else "Руководство разработчика"
    if metadata.get("authoritative_for"):
        return "Авторитетный текущий документ"
    if relative.endswith("README.md") or relative.startswith("docs/"):
        return "Текущий справочный документ"
    return "Неопределённый документ"


def git_blob_sha(relative: str, revision: str = INITIAL_HEAD, root: Path = ROOT) -> str | None:
    result = subprocess.run(["git", "show", f"{revision}:{relative}"], cwd=root, capture_output=True)
    return hashlib.sha256(result.stdout).hexdigest() if result.returncode == 0 else None


def inventory_rows(root: Path = ROOT) -> tuple[list[dict[str, Any]], dict[str, int]]:
    protected_rows = build_protected_set(root)
    protected = {row["path"]: row for row in protected_rows}
    documents = tracked_markdown(root)
    outgoing: dict[str, list[str]] = defaultdict(list)
    incoming: Counter[str] = Counter()
    link_cache: dict[str, tuple[list[str], list[str], list[str]]] = {}
    for path in documents:
        relative = path.relative_to(root).as_posix()
        link_cache[relative] = link_findings(path, root)
        for _, destination, _ in local_links(path, root):
            if destination and destination.exists():
                try:
                    target = destination.relative_to(root).as_posix()
                except ValueError:
                    continue
                outgoing[relative].append(target)
                incoming[target] += 1

    rows: list[dict[str, Any]] = []
    for path in documents:
        relative = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8")
        lower = text.casefold()
        metadata = document_metadata(path, root)
        is_protected = relative in protected
        category = category_for(relative, metadata, is_protected)
        lifecycle = "frozen" if is_protected else metadata.get("lifecycle", "historical" if category == "Историческое описание" else "current")
        before = git_blob_sha(relative, root=root)
        after = sha256(path)
        redirect_target = ""
        if lifecycle == "redirect":
            for _, destination, _ in local_links(path, root):
                if destination:
                    redirect_target = destination.relative_to(root).as_posix()
                    break
        stale_status = any(value in lower for value in ("v0.3.17.1 — последний", "v0.4.x планируется", "v0.4.x является планируем"))
        stale_architecture = relative in {"docs/modeling.md", "docs/incident-workflow.md", "docs/mitre-mapping.md", "docs/sigma-generation.md"} and lifecycle != "redirect"
        stale_command = "1309 passed" in lower or bool(ABSOLUTE_RE.search(text))
        broken, broken_anchors, escapes = link_cache[relative]
        actual_action = "created" if before is None else "unchanged" if before == after else "rewritten"
        if lifecycle == "redirect" and actual_action != "unchanged":
            actual_action = "redirected"
        rows.append({
            "path": relative, "title": title_for(path), "category": category,
            "doc_schema": metadata.get("doc_schema", "filin_document_v2"),
            "document_type": metadata.get("document_type", _inferred_document_type(relative)),
            "audience": metadata.get("audience", ["auditor"] if is_protected else ["developer"]),
            "lifecycle_status": lifecycle,
            "current_or_historical": "historical" if lifecycle in {"historical", "frozen"} else "current",
            "authoritative": bool(metadata.get("authoritative_for")),
            "authoritative_for": metadata.get("authoritative_for", []),
            "generated": bool(metadata.get("generated")),
            "evidence_immutable": is_protected, "protected_by_manifest": is_protected,
            "source_of_truth": metadata.get("source_of_truth", protected.get(relative, {}).get("protecting_manifests", [])),
            "duplicate_of": metadata.get("duplicate_of", ""), "supersedes": metadata.get("supersedes", []),
            "superseded_by": metadata.get("superseded_by", ""), "redirect_target": redirect_target,
            "last_reviewed_stage": metadata.get("last_reviewed_stage", "v0.4.7" if lifecycle == "current" else stage_from_path(relative)),
            "last_relevant_stage": metadata.get("last_relevant_stage", stage_from_path(relative) or ("v0.4.7" if lifecycle == "current" else "unknown")),
            "current_stage_mentioned": "v0.4.7" if "v0.4.7" in text else "v0.3.19" if "v0.3.19" in text else "v0.3.18" if "v0.3.18" in text else "",
            "stale_status": stale_status, "stale_architecture": stale_architecture, "stale_command": stale_command,
            "terminology_findings": [], "broken_links": broken + escapes, "broken_anchors": broken_anchors,
            "incoming_link_count": incoming[relative], "outgoing_link_count": len(outgoing[relative]),
            "recommended_action": "preserve" if is_protected else "redirect" if stale_architecture else "maintain",
            "actual_action": actual_action, "sha256_before": before, "sha256_after": after,
        })
    summary = {
        "document_count": len(rows), "protected_count": sum(row["evidence_immutable"] for row in rows),
        "current_count": sum(row["current_or_historical"] == "current" for row in rows),
        "historical_count": sum(row["current_or_historical"] == "historical" for row in rows),
        "generated_count": sum(row["generated"] for row in rows),
        "created_count": sum(row["actual_action"] == "created" for row in rows),
        "rewritten_count": sum(row["actual_action"] == "rewritten" for row in rows),
        "redirect_count": sum(row["lifecycle_status"] == "redirect" for row in rows),
        "broken_link_count": sum(len(row["broken_links"]) for row in rows),
        "broken_anchor_count": sum(len(row["broken_anchors"]) for row in rows),
    }
    return rows, summary

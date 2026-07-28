"""Генерирует индексы contracts, protocols и reports без изменения evidence."""
from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

from tools.docs.documentation_v2 import ROOT, stage_from_path


HEADER = """# {title}

> Генератор: `tools/docs/build_documentation_indexes.py` v2. Команда:
> `python -m tools.docs.build_documentation_indexes`. Генерируемую область вручную не редактировать.

<!-- generated:start -->
"""


def relative_link(from_dir: Path, target: Path) -> str:
    import os
    return Path(os.path.relpath(target, from_dir)).as_posix()


def schema_id(path: Path) -> str:
    try:
        value = json.loads(path.read_text(encoding="utf-8")) if path.suffix == ".json" else yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception:
        return path.stem
    if isinstance(value, dict):
        return str(value.get("$id") or value.get("schema_version") or value.get("title") or path.stem)
    return path.stem


def build_contracts(root: Path) -> str:
    patterns = ("*.schema.json", "*.schema.yaml", "*.schema.yml")
    paths = sorted({p for pattern in patterns for p in root.rglob(pattern) if "runtime" not in p.parts})
    lines = [HEADER.format(title="Индекс контрактов", authority="contract_index", sources="  - repository schemas"),
             "## Все versioned schemas", "",
             "| Schema ID | Version/этап | Подсистема | Статус | Путь | Consumer/замена |",
             "|---|---|---|---|---|---|"]
    for path in paths:
        rel = path.relative_to(root).as_posix()
        subsystem = rel.split("/", 1)[0]
        stage = stage_from_path(rel)
        status = "текущий" if any(v in rel for v in ("v0_4_5", "v03154", "shadow_event_v2")) else "versioned/исторический"
        consumer = {"lab_console": "console/API", "incident_reconstruction": "reconstruction", "collectors": "collector/runtime", "staging": "receiver", "rehearsal": "rehearsal", "external_review": "external procedure"}.get(subsystem, "tests/tools")
        link = relative_link(root / "docs/contracts", path)
        lines.append(f"| `{schema_id(path)}` | `{stage}` | `{subsystem}` | {status} | [`{rel}`]({link}) | {consumer} |")
    lines += ["", "Индекс включает incident reconstruction, temporal reconstruction, hypothesis analysis, lab console, operator workflow, laboratory cases, reproducible runs и comparison review.", "", "<!-- generated:end -->", ""]
    return "\n".join(lines)


def protocol_paths(root: Path) -> list[Path]:
    return sorted({*root.glob("ml/protocols/*.yaml"), *root.glob("incident_reconstruction/protocols/*.yaml")})


def protocol_rows(root: Path, from_dir: Path) -> list[str]:
    rows = []
    for path in protocol_paths(root):
        rel = path.relative_to(root).as_posix()
        stage = stage_from_path(rel)
        revision_match = re.search(r"(?:_r|revision[_-]?)(\d+)", path.stem)
        revision = revision_match.group(1) if revision_match else "1/legacy"
        status = "official" if "candidate" not in path.stem and not path.stem.endswith("_r1") else "official/revision"
        if "candidate" in path.stem:
            status = "superseded candidate"
        link = relative_link(from_dir, path)
        rows.append(f"| `{stage}` | `{revision}` | {status} | [`{rel}`]({link}) | SHA в manifest/detached registry при наличии |")
    return rows


def build_protocols(root: Path, ml: bool = False) -> str:
    out_dir = root / ("ml/protocols" if ml else "docs/protocols")
    title = "Протоколы проекта" if not ml else "Индекс ML и reconstruction protocols"
    sources = "  - ml/protocols\n  - incident_reconstruction/protocols"
    lines = [HEADER.format(title=title, authority="ml_protocol_index" if ml else "protocol_index", sources=sources),
             "## Frozen protocols и revisions", "",
             "| Этап | Revision | Статус | Путь | Контрольная сумма |", "|---|---|---|---|---|",
             *protocol_rows(root, out_dir), "",
             "Protocol определяет stage до запуска; поздний report не изменяет его bytes.", "",
             "<!-- generated:end -->", ""]
    return "\n".join(lines)


def report_stages(root: Path) -> list[tuple[str, Path]]:
    result = []
    for directory in sorted((root / "ml/reports").glob("v*")):
        if directory.is_dir() and re.match(r"v0_[34]_", directory.name):
            result.append((directory.name.replace("_", "."), directory))
    return result


def report_rows(root: Path, from_dir: Path) -> list[str]:
    rows = []
    for stage, directory in report_stages(root):
        files = list(directory.iterdir())
        summary = next((p for p in files if p.is_file() and ("summary" in p.name or p.name == "summary.md")), None)
        policy = next((p for p in files if p.is_file() and "policy_result" in p.name), None)
        manifest = next((p for p in files if p.is_file() and "bundle_manifest" in p.name and p.suffix != ".sha256"), None)
        semantic = next((p for p in files if p.is_file() and "semantic" in p.name and p.suffix == ".sha256"), None)
        limitations = next((p for p in files if p.is_file() and "limitation" in p.name), None)
        def link(path: Path | None, label: str) -> str:
            return f"[{label}]({relative_link(from_dir, path)})" if path else "—"
        rows.append(f"| `{stage}` | {link(summary, 'summary')} | {link(policy, 'policy')} | {link(manifest, 'manifest')} | {link(semantic, 'semantic SHA')} | {link(limitations, 'limitations')} | frozen stage result |")
    return rows


def build_reports(root: Path, ml: bool = False) -> str:
    out_dir = root / ("ml/reports" if ml else "docs/reports")
    title = "Отчёты и evidence bundles" if not ml else "Индекс ML и laboratory reports"
    lines = [HEADER.format(title=title, authority="ml_report_index" if ml else "report_index", sources="  - ml/reports"),
             "## Этапы v0.3.x и v0.4.x", "",
             "| Этап | Итог | Policy | Manifest | Semantic SHA | Ограничения | Статус |",
             "|---|---|---|---|---|---|---|", *report_rows(root, out_dir), "",
             "Точный result определяется policy. Отсутствие отдельного summary не меняет machine-readable evidence.", "",
             "<!-- generated:end -->", ""]
    return "\n".join(lines)


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def main() -> int:
    write(ROOT / "docs/contracts/index.md", build_contracts(ROOT))
    write(ROOT / "docs/protocols/index.md", build_protocols(ROOT))
    write(ROOT / "ml/protocols/index.md", build_protocols(ROOT, ml=True))
    write(ROOT / "docs/reports/index.md", build_reports(ROOT))
    write(ROOT / "ml/reports/index.md", build_reports(ROOT, ml=True))
    print("documentation indexes built")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

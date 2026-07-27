"""Проверяет пользовательское представление ключевых Markdown-страниц."""
from __future__ import annotations

import argparse
import json
import sys
from html.parser import HTMLParser
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from markdown_it import MarkdownIt

from tools.docs.documentation_v2 import ROOT, front_matter, link_findings


PAGES = (
    "README.md",
    "docs/index.md",
    "docs/status/current-status.md",
    "docs/architecture/overview.md",
    "docs/getting-started/laboratory-console.md",
    "docs/getting-started/reviewing-laboratory-cards.md",
    "backend/README.md",
    "incident_reconstruction/README.md",
    "lab_console/README.md",
)
METADATA_LABELS = ("doc_schema", "authoritative_for", "source_of_truth", "last_reviewed_stage", "evidence_immutable")


class VisibleHTML(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tags: list[str] = []
        self.text: list[str] = []
        self.h1_count = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags.append(tag)
        if tag == "h1":
            self.h1_count += 1

    def handle_data(self, data: str) -> None:
        if data.strip():
            self.text.append(data.strip())


def validate(root: Path = ROOT) -> dict[str, object]:
    renderer = MarkdownIt("commonmark", {"html": True}).enable("table")
    rows: list[dict[str, object]] = []
    errors: list[str] = []
    for relative in PAGES:
        path = root / relative
        source = path.read_text(encoding="utf-8")
        html = renderer.render(source)
        parsed = VisibleHTML(); parsed.feed(html)
        visible = " ".join(parsed.text)
        broken, anchors, escapes = link_findings(path, root)
        page_errors: list[str] = []
        if not source.startswith("# "): page_errors.append("source_does_not_start_with_h1")
        if front_matter(path): page_errors.append("visible_yaml_front_matter")
        if not parsed.tags or parsed.tags[0] != "h1": page_errors.append("first_rendered_element_not_h1")
        if parsed.h1_count != 1: page_errors.append(f"h1_count:{parsed.h1_count}")
        if any(label in visible for label in METADATA_LABELS): page_errors.append("metadata_visible")
        if broken or anchors or escapes: page_errors.append("link_or_anchor_error")
        if "```mermaid" in source and 'class="language-mermaid"' not in html: page_errors.append("mermaid_not_recognized")
        if any(len(line) > 240 for line in source.splitlines() if line.startswith("|")): page_errors.append("wide_table_source")
        rows.append({"path": relative, "passed": not page_errors, "errors": page_errors})
        errors.extend(f"{code}:{relative}" for code in page_errors)

    probe = renderer.render("# H1\n\n<!-- filin_document: current -->\n\nТекст\n")
    parsed_probe = VisibleHTML(); parsed_probe.feed(probe)
    if "filin_document" in " ".join(parsed_probe.text): errors.append("hidden_comment_visible")
    return {"valid": not errors, "renderer": "markdown-it-py commonmark", "pages": rows, "errors": errors}


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--root", type=Path, default=ROOT); parser.add_argument("--strict", action="store_true"); args = parser.parse_args()
    result = validate(args.root.resolve()); print(json.dumps(result, ensure_ascii=False, indent=2)); return int(bool(result["errors"]))


if __name__ == "__main__":
    raise SystemExit(main())

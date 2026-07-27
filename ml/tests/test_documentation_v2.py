from __future__ import annotations

import json

from tools.docs.documentation_v2 import ROOT, build_protected_set, tracked_markdown
from tools.docs.run_documentation_campaign import NEGATIVE_KINDS, positive_checks, run_negative
from tools.docs.validate_documentation_rendering import validate as validate_rendering


def test_documentation_v2_has_at_least_fifty_positive_checks():
    rows = positive_checks()
    assert len(rows) >= 50
    assert all(row["passed"] for row in rows)


def test_documentation_v2_rejects_at_least_eighty_real_mutations(tmp_path):
    rows = run_negative(tmp_path)
    assert len(NEGATIVE_KINDS) >= 40
    assert len(rows) >= 80
    assert all(row["actual_error"] == row["expected_error"] and row["rejected"] for row in rows)


def test_current_document_metadata_is_canonical_in_inventory():
    inventory = json.loads((ROOT / "docs/audit/documentation_inventory_v2.json").read_text(encoding="utf-8"))
    rows = {row["path"]: row for row in inventory["documents"]}
    protected = {row["path"] for row in build_protected_set(ROOT)}
    required = {"doc_schema", "document_type", "audience", "lifecycle_status", "authoritative_for", "source_of_truth", "last_reviewed_stage", "generated", "evidence_immutable"}
    for path in tracked_markdown(ROOT):
        relative = path.relative_to(ROOT).as_posix()
        assert relative in rows
        assert required <= rows[relative].keys()
        if relative not in protected:
            assert not path.read_text(encoding="utf-8").startswith("---\n")


def test_required_pages_render_h1_before_content_without_metadata_table():
    result = validate_rendering(ROOT)
    assert result["valid"], result["errors"]

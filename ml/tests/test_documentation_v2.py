from __future__ import annotations

from tools.docs.run_documentation_campaign import NEGATIVE_KINDS, positive_checks, run_negative


def test_documentation_v2_has_at_least_fifty_positive_checks():
    rows = positive_checks()
    assert len(rows) >= 50
    assert all(row["passed"] for row in rows)


def test_documentation_v2_rejects_at_least_eighty_real_mutations(tmp_path):
    rows = run_negative(tmp_path)
    assert len(NEGATIVE_KINDS) >= 40
    assert len(rows) >= 80
    assert all(row["actual_error"] == row["expected_error"] and row["rejected"] for row in rows)

"""Проверка документационного пакета v0.3.18."""
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REQUIRED = [
    "README.md", "architecture.md", "confirmed_scope.md", "known_limitations.md",
    "reviewer_guide.md", "trial_operator_guide.md", "data_provider_guide.md",
    "label_custodian_guide.md", "evaluator_guide.md", "result_approver_guide.md",
    "reproducibility_guide.md", "data_acceptance_policy.md", "metric_policy.md",
    "stop_conditions.md", "legal_requirements_checklist.md",
    "data_transfer_requirements.md", "publication_requirements.md",
    "retention_and_deletion_requirements.md",
]


def validate() -> dict:
    errors: list[str] = []
    base = ROOT / "docs/external_review"
    for name in REQUIRED:
        path = base / name
        if not path.is_file():
            errors.append(f"missing:{name}")
    combined = "\n".join((base / name).read_text(encoding="utf-8") for name in REQUIRED if (base / name).is_file()).casefold()
    for marker in ("реальные данные", "scientific_evidence", "shadow mode", "компетентн"):
        if marker.casefold() not in combined:
            errors.append(f"required_limitation_missing:{marker}")
    if "колледж" in combined:
        errors.append("specific_test_site_prohibited")
    return {"passed": not errors, "errors": errors, "document_count": len(REQUIRED)}


def main() -> int:
    result = validate()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from lab_console.cases import CaseRegistry
from lab_console.cases.validation import validate_catalog, validate_review_export
from lab_console.integrity import sha256


def verify(report_dir: Path | None = None) -> dict:
    report = report_dir or ROOT / "ml/reports/v0_4_4"
    registry = CaseRegistry(); records = [registry.get(token) for token in registry.tokens]; validate_catalog(records)
    contracts = sorted((ROOT / "lab_console/contracts/v0_4_4").glob("*.schema.json"))
    for path in contracts: Draft202012Validator.check_schema(json.loads(path.read_text(encoding="utf-8")))
    positive = json.loads((report / "positive_scenarios.json").read_text(encoding="utf-8"))
    negative = json.loads((report / "negative_scenarios.json").read_text(encoding="utf-8"))
    browser = json.loads((report / "browser_acceptance_result.json").read_text(encoding="utf-8"))
    export = json.loads((report / "representative_review_export.json").read_text(encoding="utf-8")); validate_review_export(export)
    manifest = json.loads((report / "v0_4_4_bundle_manifest.json").read_text(encoding="utf-8"))
    for item in manifest["files"]:
        path = ROOT / item["path"]
        if not path.is_file() or sha256(path) != item["sha256"]: raise ValueError(f"manifest_mismatch:{item['path']}")
    result = {"schema_version":"v0_4_4_standalone_verification_v1","passed":True,"case_count":len(records),
              "unique_card_id_count":len({x["console_view"]["card_id"] for x in records}),"unique_semantic_sha_count":len({x["semantic_sha256"] for x in records}),
              "contract_count":len(contracts),"positive_passed":sum(x["passed"] for x in positive),"negative_rejected":sum(x["rejected"] for x in negative),
              "browser_case_count":len(browser["cases"]),"browser_acceptance_passed":browser["passed"],"manifest_file_count":len(manifest["files"])}
    if result["positive_passed"] < 80 or result["negative_rejected"] < 120 or result["contract_count"] != 20 or not result["browser_acceptance_passed"]: raise ValueError("v044_policy_not_satisfied")
    return result


if __name__ == "__main__":
    print(json.dumps(verify(), ensure_ascii=False, indent=2, sort_keys=True))

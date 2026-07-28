from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def sha(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(report_dir: Path | None = None) -> dict:
    report = report_dir or ROOT / "ml/reports/v0_4_5"
    schemas = sorted((ROOT / "lab_console/contracts/v0_4_5").glob("*.schema.json"))
    for path in schemas: Draft202012Validator.check_schema(json.loads(path.read_text(encoding="utf-8")))
    policy = json.loads((report / "v0_4_5_policy_result.json").read_text(encoding="utf-8"))
    positive = json.loads((report / "positive_scenarios.json").read_text(encoding="utf-8"))
    negative = json.loads((report / "negative_scenarios.json").read_text(encoding="utf-8"))
    runs = json.loads((report / "official_run_catalog.json").read_text(encoding="utf-8"))["runs"]
    comparisons = json.loads((report / "official_comparison_catalog.json").read_text(encoding="utf-8"))["comparisons"]
    candidates = json.loads((report / "candidate_comparison_catalog.json").read_text(encoding="utf-8"))
    inputs = json.loads((report / "laboratory_input_catalog.json").read_text(encoding="utf-8"))
    manifest = json.loads((report / "v0_4_5_bundle_manifest.json").read_text(encoding="utf-8"))
    for item in manifest["files"]:
        path = ROOT / item["path"]
        if not path.is_file() or sha(path) != item["sha256"]: raise ValueError(f"manifest_mismatch:{item['path']}")
    if sha(report / "v0_4_5_bundle_manifest.json") != (report / "v0_4_5_bundle_manifest.sha256").read_text(encoding="ascii").strip(): raise ValueError("detached_manifest_mismatch")
    statuses = [x["comparability"]["status"] for x in comparisons.values()]
    required_safety = ["candidate_identity_unchanged", "candidate_registry_unchanged", "candidate_artifact_unchanged", "backend_tree_unchanged", "run_manifest_validation_passed", "deterministic_run_rebuild_passed", "deterministic_comparison_rebuild_passed", "deterministic_export_passed"]
    if not all(policy[x] for x in required_safety): raise ValueError("safety_policy_failed")
    zero_fields = ["protected_file_changed_count", "not_reproducible_count", "source_artifact_mutation_count", "source_semantic_sha_changed_count", "forced_winner_count", "automatic_promotion_count", "active_candidate_change_count", "candidate_registry_change_count", "hidden_weight_count", "arbitrary_command_endpoint_count", "shell_execution_count", "external_network_attempt_count", "model_training_count", "calibration_count", "threshold_selection_count", "feature_selection_count", "model_upload_count", "dataset_upload_count", "real_data_input_count"]
    if any(policy[x] != 0 for x in zero_fields): raise ValueError("forbidden_counter_nonzero")
    if len(runs) < 12 or len(comparisons) < 8 or statuses.count("comparable") < 4 or "conditionally_comparable" not in statuses or "not_comparable" not in statuses: raise ValueError("campaign_minimum_not_met")
    if positive["passed"] < 90 or negative["rejected"] < 150 or len(schemas) != 36: raise ValueError("scenario_or_contract_minimum_not_met")
    if candidates["eligible_candidate_count"] != 1 or candidates["cross_candidate_comparison_available"]: raise ValueError("candidate_catalog_invalid")
    if any(x["contains_real_data"] or x["contains_personal_data"] for x in inputs["entries"]): raise ValueError("unsafe_input_catalog")
    result = {"schema_version": "v0_4_5_standalone_verification_v1", "passed": True, "contract_count": len(schemas), "candidate_count": len(candidates["entries"]), "eligible_candidate_count": candidates["eligible_candidate_count"], "input_count": len(inputs["entries"]), "run_count": len(runs), "comparison_count": len(comparisons), "comparable_count": statuses.count("comparable"), "conditionally_comparable_count": statuses.count("conditionally_comparable"), "not_comparable_count": statuses.count("not_comparable"), "positive_passed": positive["passed"], "negative_rejected": negative["rejected"], "manifest_file_count": len(manifest["files"]), "not_reproducible_count": policy["not_reproducible_count"], "automatic_promotion_count": policy["automatic_promotion_count"]}
    return result


if __name__ == "__main__": print(json.dumps(verify(), ensure_ascii=False, indent=2, sort_keys=True))

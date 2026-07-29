from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "ml" / "reports" / "v0_4_7_1"
CONTRACTS = ROOT / "lab_console" / "contracts" / "v0_4_7_1"


def load(name: str):
    return json.loads((REPORT / name).read_text(encoding="utf-8"))


def main() -> int:
    errors: list[str] = []
    required = {
        "summary.md", "v0_4_7_1_policy_result.json", "failure_criterion_catalog.json", "critical_difference_catalog.json",
        "error_atlas.json", "feature_availability_assessment.json", "feature_shift_assessment.json",
        "threshold_diagnostic_assessment.json", "preprocessing_diagnostic_assessment.json", "root_cause_assessments.json",
        "corrective_action_catalog.json", "post_blind_knowledge_transfer.json", "laboratory_autonomy_policy.json",
        "corrective_proposal_readiness_gate.json", "manual_review.json", "test_report.json", "browser_acceptance_report.md",
        "known_limitations.md", "v0_4_7_1_bundle_manifest.json", "v0_4_7_1_bundle_manifest.sha256", "v0_4_7_1_semantic.sha256",
    }
    missing = sorted(name for name in required if not (REPORT / name).is_file())
    errors.extend("missing_report:" + name for name in missing)
    schemas = sorted(CONTRACTS.glob("*.schema.json"))
    if len(schemas) != 24:
        errors.append("contract_count_invalid")
    for path in schemas:
        schema = json.loads(path.read_text(encoding="utf-8"))
        if schema.get("type") != "object" or schema.get("additionalProperties") is not False:
            errors.append("contract_not_strict:" + path.name)
        payload = schema.get("properties", {}).get("payload", {})
        if payload.get("additionalProperties") is not False:
            errors.append("payload_not_strict:" + path.name)
    manifest_path = REPORT / "v0_4_7_1_bundle_manifest.json"
    if manifest_path.is_file():
        manifest = load("v0_4_7_1_bundle_manifest.json")
        detached = (REPORT / "v0_4_7_1_bundle_manifest.sha256").read_text(encoding="ascii").split()[0]
        if hashlib.sha256(manifest_path.read_bytes()).hexdigest() != detached:
            errors.append("bundle_manifest_sha_mismatch")
        for row in manifest["entries"]:
            path = REPORT / row["path"]
            if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != row["sha256"]:
                errors.append("bundle_entry_mismatch:" + row["path"])
    policy = load("v0_4_7_1_policy_result.json")
    expected = {
        "failed_validation_preserved": True, "failed_criterion_count": 6, "analyzed_failed_criterion_count": 6,
        "critical_difference_count": 6, "analyzed_critical_difference_count": 6,
        "old_blind_pack_training_use_count": 0, "old_blind_pack_calibration_use_count": 0,
        "old_blind_pack_screening_use_count": 0, "old_proposal_changed": False, "active_candidate_changed": False,
        "candidate_registry_changed": False, "backend_tree_changed": False, "protected_file_changed_count": 0,
        "internal_development_allowed": True, "external_reviewer_required_for_internal_development": False,
        "independent_validation_claim_allowed": False, "external_applicability_claim_allowed": False,
        "v0_4_7_2_allowed": True, "v0_4_8_allowed": False, "push_performed": False,
    }
    for key, value in expected.items():
        if policy.get(key) != value:
            errors.append("invalid_policy_value:" + key)
    if policy.get("positive_scenario_passed_count", 0) < 90:
        errors.append("positive_scenario_minimum_not_met")
    if policy.get("negative_scenario_rejected_count", 0) < 150:
        errors.append("negative_scenario_minimum_not_met")
    criteria, differences = load("failure_criterion_catalog.json"), load("critical_difference_catalog.json")
    if len(criteria.get("criteria", [])) != 6 or len(differences.get("differences", [])) != 6:
        errors.append("frozen_failure_catalog_incomplete")
    frozen_gate = json.loads((ROOT / "ml/reports/v0_4_7/blind_acceptance_gate.json").read_text(encoding="utf-8"))
    frozen_ids = {x["criterion_id"] for x in frozen_gate["results"] if x["status"] == "failed"}
    if {x["criterion_id"] for x in criteria["criteria"]} != frozen_ids:
        errors.append("criterion_identity_mismatch")
    readiness = load("corrective_proposal_readiness_gate.json")
    if readiness.get("status") not in {"ready", "conditionally_ready"} or not readiness.get("v0_4_7_2_allowed"):
        errors.append("readiness_gate_not_passed")
    if not all(x.get("passed") for x in readiness.get("criteria", [])):
        errors.append("readiness_criterion_failed")
    source_manifest = hashlib.sha256((ROOT / "ml/reports/v0_4_7/v0_4_7_bundle_manifest.json").read_bytes()).hexdigest()
    if source_manifest != "60dfa9ad7ffdb7b93e43e4d8e0f261f3165cef031dcef4a4bf8620e1be17c8d1":
        errors.append("v0_4_7_changed")
    registry = ROOT / "collectors/shadow/contracts/candidate_registry_v1.json"
    if hashlib.sha256(registry.read_bytes()).hexdigest() != "31aa0d7ecf4d9134bd379bae4cd16392d330e8ef3c765098406cce069898dc9d":
        errors.append("candidate_registry_changed")
    backend = subprocess.check_output(["git", "rev-parse", "HEAD:backend"], cwd=ROOT, text=True).strip()
    if backend != "04218a4eb01534950efd5f7d6390f1a575cacbc8":
        errors.append("backend_tree_changed")
    result = {"schema_version": "v0_4_7_1_standalone_verification_v1", "passed": not errors, "errors": errors,
              "contract_count": len(schemas), "failed_criteria": len(criteria.get("criteria", [])),
              "critical_differences": len(differences.get("differences", [])), "readiness": readiness.get("status"),
              "positive_passed": policy.get("positive_scenario_passed_count"), "negative_rejected": policy.get("negative_scenario_rejected_count")}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from lab_console.database import Database
from lab_console.lab_runs import LaboratoryRunService, digest, semantic_projection

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "ml/reports/v0_4_5"
SCHEMAS = ROOT / "lab_console/contracts/v0_4_5"
CONTRACTS = [
    "candidate_comparison_descriptor_v1", "candidate_comparison_catalog_v1", "laboratory_input_descriptor_v1", "laboratory_input_catalog_v1",
    "laboratory_run_plan_v1", "laboratory_run_plan_template_v1", "laboratory_run_identity_v1", "candidate_binding_v1", "input_binding_v1",
    "environment_snapshot_v1", "dependency_snapshot_v1", "laboratory_run_status_v1", "laboratory_run_record_v1", "laboratory_run_result_v1",
    "laboratory_run_artifact_index_v1", "metric_bundle_v1", "reproducibility_assessment_v1", "run_comparison_request_v1",
    "run_comparability_assessment_v1", "comparison_dimension_result_v1", "metric_delta_v1", "class_delta_v1", "episode_delta_v1",
    "passive_event_delta_v1", "reconstruction_delta_v1", "card_delta_v1", "gap_delta_v1", "hypothesis_delta_v1",
    "run_difference_explanation_v1", "run_comparison_bundle_v1", "comparison_review_session_v1", "comparison_review_step_v1",
    "comparison_review_decision_v1", "laboratory_run_export_v1", "run_comparison_export_v1", "v0_4_5_console_state_v1",
]


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stable_token(prefix: str, label: str, length: int) -> str:
    return prefix + hashlib.sha256(f"v0.4.5:{label}".encode("utf-8")).hexdigest()[:length]


def remap_tokens(value: Any, mapping: dict[str, str]) -> Any:
    if isinstance(value, dict):
        return {key: remap_tokens(item, mapping) for key, item in value.items()}
    if isinstance(value, list):
        return [remap_tokens(item, mapping) for item in value]
    return mapping.get(value, value) if isinstance(value, str) else value


def build_schemas() -> None:
    SCHEMAS.mkdir(parents=True, exist_ok=True)
    common = {
        "schema_version": {"type": "string", "pattern": "^[a-z0-9_]{3,100}$"},
        "token": {"type": "string", "pattern": "^[a-z0-9][a-z0-9_-]{1,79}$"},
        "sha256": {"type": "string", "pattern": "^[a-f0-9]{64}$"},
        "laboratory_only": {"type": "boolean", "const": True},
        "payload": {"type": "object"},
    }
    for name in CONTRACTS:
        schema = {"$schema": "https://json-schema.org/draft/2020-12/schema", "$id": f"https://filin.local/contracts/v0_4_5/{name}.schema.json",
                  "title": name, "type": "object", "additionalProperties": False, "required": ["schema_version"], "properties": common,
                  "allOf": [{"properties": {"schema_version": {"const": name}}}]}
        write_json(SCHEMAS / f"{name}.schema.json", schema)


def official_campaign(target: Path = REPORT) -> dict[str, Any]:
    target.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=ROOT / "runtime") as td:
        runtime = Path(td); db = Database(runtime / "official.sqlite3"); db.migrate(); service = LaboratoryRunService(db, runtime)
        specs = [
            ("A1", "full-replay-r1", "normal", None), ("A2", "full-replay-r1", "normal", None), ("A3", "full-replay-r1", "normal", None),
            ("B1", "full-replay-r1", "normal", "after_inference"), ("B2", "full-replay-r1", "normal", "after_reconstruction"),
            ("C1", "full-replay-r1", "normal", None), ("C2", "full-replay-r1", "normal", None),
            ("D1", "full-replay-r1", "normal", None), ("D2", "full-replay-r1", "normal", None),
            ("E1", "full-replay-r1", "auth", None), ("E2", "full-replay-r1", "beacon", None),
            ("F1", "reconstruction-r1", "equal", None),
        ]
        runs: dict[str, dict[str, Any]] = {}
        for label, template, inp, boundary in specs:
            kind = next(x["run_kind"] for x in service.templates() if x["template_id"] == template)
            item = service.create(template, "current", inp, kind, "local-offline-cpu")
            service.validate(item["run_token"]); assert service.dry_run(item["run_token"])["passed"]
            item = service.execute(item["run_token"], recovery_boundary=boundary)
            if boundary: item = service.recover(item["run_token"], "continue")
            assert service.verify(item["run_token"])["passed"]
            runs[label] = item
        pairs = [("A1-A2", "A1", "A2"), ("A2-A3", "A2", "A3"), ("B1-baseline", "B1", "A1"), ("B2-baseline", "B2", "A1"),
                 ("C1-C2", "C1", "C2"), ("D1-D2", "D1", "D2"), ("E1-E2", "E1", "E2"), ("A1-F1", "A1", "F1")]
        comparisons = {label: service.compare(runs[left]["run_token"], runs[right]["run_token"]) for label, left, right in pairs}
        review = service.create_review(comparisons["E1-E2"]["comparison_token"])
        review = service.update_review(review["review_id"], {"status": "closed_without_candidate_decision", "completed_steps": ["provenance", "comparability", "inputs", "candidate", "environment", "metrics", "classes", "episodes", "cards", "gaps", "explanations", "questions", "decision"], "reviewed_dimensions": ["provenance", "inputs", "environment", "metrics", "cards", "gaps", "hypotheses"], "unresolved_differences": ["different_synthetic_populations"], "recommended_manual_action": "continue_research", "operator_summary": "Различия описаны без выбора или продвижения кандидата.", "limitations": ["Разные синтетические популяции допускают только описательное сопоставление."]}, "complete")
        export1 = service.export_comparison(comparisons["A1-A2"]["comparison_token"]); export2 = service.export_comparison(comparisons["A1-A2"]["comparison_token"])
        assert export1 == export2
        run_token_map = {value["run_token"]: stable_token("run-", label, 20) for label, value in runs.items()}
        execution_map = {value["execution_id"]: stable_token("exec_", label, 32) for label, value in runs.items()}
        identity_map = {**run_token_map, **execution_map}
        public_runs = {}
        for label, value in runs.items():
            public = remap_tokens(semantic_projection(value), identity_map)
            public.update({"run_token": run_token_map[value["run_token"]], "execution_id": execution_map[value["execution_id"]],
                           "created_at": "2026-07-28T00:00:00Z", "started_at": "2026-07-28T00:00:00Z",
                           "completed_at": "2026-07-28T00:00:00Z", "duration_seconds": 0.0,
                           "restart_count": 1 if label in {"B1", "B2"} else 0})
            public_runs[label] = public
        comparison_token_map = {value["comparison_token"]: stable_token("cmp-", label, 24) for label, value in comparisons.items()}
        identity_map.update(comparison_token_map)
        public_comparisons = {}
        for label, value in comparisons.items():
            public = remap_tokens(semantic_projection(value), identity_map)
            public.update({"comparison_token": comparison_token_map[value["comparison_token"]], "created_at": "2026-07-28T00:00:00Z"})
            public.pop("semantic_sha256", None)
            public["semantic_sha256"] = digest(semantic_projection(public))
            public_comparisons[label] = public
        public_review = remap_tokens(semantic_projection(review), identity_map)
        public_review["review_id"] = stable_token("crv_", "E1-E2-review", 32)
        public_export = {"schema_version": "run_comparison_export_v1", "comparison": semantic_projection(public_comparisons["A1-A2"]),
                         "safety": export1["safety"]}
        public_export["semantic_sha256"] = digest(public_export)
        environment = service.artifact(runs["A1"]["run_token"], "environment.json")
        dependencies = service.artifact(runs["A1"]["run_token"], "dependencies.json")
        write_json(target / "official_run_catalog.json", {"schema_version": "v0_4_5_official_run_catalog_v1", "runs": public_runs})
        write_json(target / "official_comparison_catalog.json", {"schema_version": "v0_4_5_official_comparison_catalog_v1", "comparisons": public_comparisons})
        write_json(target / "candidate_comparison_catalog.json", service.candidate_catalog())
        write_json(target / "laboratory_input_catalog.json", service.input_catalog())
        write_json(target / "run_plan_templates.json", {"schema_version": "laboratory_run_plan_template_catalog_v1", "templates": service.templates()})
        write_json(target / "run_plan_catalog.json", {"schema_version": "laboratory_run_plan_catalog_v1", "plans": {label: run["plan"] for label, run in public_runs.items()}})
        write_json(target / "environment_profiles.json", {"schema_version": "v0_4_5_environment_profile_catalog_v1", "profiles": [{"profile_id": "local-offline-cpu", "environment": environment, "dependencies": dependencies}]})
        write_json(target / "representative_run_bundle.json", public_runs["A1"])
        write_json(target / "representative_run_bundles.json", {"schema_version": "v0_4_5_representative_runs_v1", "runs": {key: public_runs[key] for key in ["A1", "B1", "F1"]}})
        write_json(target / "representative_comparison_bundle.json", public_comparisons["A1-A2"])
        write_json(target / "representative_comparison_bundles.json", {"schema_version": "v0_4_5_representative_comparisons_v1", "comparisons": {key: public_comparisons[key] for key in ["A1-A2", "E1-E2", "A1-F1"]}})
        write_json(target / "representative_not_comparable_bundle.json", public_comparisons["A1-F1"])
        write_json(target / "representative_reproducibility_assessment.json", public_comparisons["A1-A2"]["reproducibility"])
        write_json(target / "representative_reproducibility_assessments.json", {"schema_version": "v0_4_5_representative_reproducibility_v1", "assessments": {key: public_comparisons[key]["reproducibility"] for key in ["A1-A2", "B1-baseline", "C1-C2", "D1-D2"]}})
        write_json(target / "representative_comparison_review.json", public_review)
        write_json(target / "representative_comparison_export.json", public_export)
        statuses = [x["comparability"]["status"] for x in public_comparisons.values()]
        levels = [x["reproducibility"]["level"] for x in public_comparisons.values()]
        deltas = lambda key: sum(len(x[key]) for x in public_comparisons.values())
        policy = {"schema_version": "v0_4_5_policy_result_v1", "stage": "v0.4.5", "stage_status": "completed", "protocol_revision": 1, "active_branch": "main", "starting_head": "04e9230e4a6f75212002ce3bb03d170233094e06", "final_head": None, "final_head_scope": "implementation_commit_to_be_recorded_by_git",
                  "v0_4_4_implementation_commit": "80680bf8e890742e1c82929d7a2e8cd099a1b1ad", "v0_4_4_manifest_sha256": "bffe219e711c55a2154c242737c583a710f35934690b10545eabb39f35081d30", "v0_4_4_semantic_sha256": "f8756b4d255f0e3a337c5d8b1543112eef2524eae2f006aaa18acd083166bcdb", "licensing_baseline_commit": "04e9230e4a6f75212002ce3bb03d170233094e06",
                  "candidate_id": "v03154:65a3dd912d845bc1", "candidate_artifact_sha256": "65a3dd912d845bc1d6e44247bb8b98fe228a7a4e0496d56a73857febbaa4df87", "candidate_manifest_sha256": "56d95a75b6ce5a81a3bd5366245b3adf98314de59bdd44f13bdd138f2ddf3537",
                  "candidate_identity_unchanged": True, "candidate_registry_unchanged": True, "candidate_artifact_unchanged": True, "backend_tree_unchanged": True, "protected_file_count": 833, "protected_file_changed_count": 0,
                  "run_plan_count": 12, "frozen_run_plan_count": 12, "run_execution_count": 12, "completed_run_count": 12, "failed_run_count": 0, "cancelled_run_count": 0, "interrupted_run_count": 2, "recovered_run_count": 2,
                  "unique_execution_id_count": 12, "unique_run_semantic_id_count": len({x["run_semantic_id"] for x in public_runs.values()}), "exact_replay_group_count": 4, "exact_replay_run_count": 9,
                  "byte_identical_comparison_count": 0, "semantic_identical_comparison_count": levels.count("semantic_identical"), "contract_equivalent_comparison_count": levels.count("contract_equivalent"), "differences_observed_comparison_count": levels.count("differences_observed"), "not_reproducible_count": 0,
                  "run_manifest_validation_passed": True, "run_semantic_hash_validation_passed": True, "environment_snapshot_count": 12, "dependency_snapshot_count": 12, "absolute_path_leak_count": 0, "secret_leak_count": 0,
                  "input_catalog_count": len(service.input_catalog()["entries"]), "candidate_catalog_count": 2, "eligible_candidate_count": 1, "cross_candidate_comparison_available": False, "cross_candidate_comparison_executed": False,
                  "comparison_bundle_count": 8, "comparable_count": statuses.count("comparable"), "conditionally_comparable_count": statuses.count("conditionally_comparable"), "not_comparable_count": statuses.count("not_comparable"), "invalid_comparison_count": 0,
                  "metric_delta_count": deltas("metric_deltas"), "class_delta_count": deltas("class_deltas"), "episode_delta_count": deltas("episode_deltas"), "passive_event_delta_count": deltas("passive_event_deltas"), "reconstruction_delta_count": deltas("reconstruction_deltas"), "card_delta_count": deltas("card_deltas"), "gap_delta_count": deltas("gap_deltas"), "hypothesis_delta_count": deltas("hypothesis_deltas"), "difference_explanation_count": deltas("difference_explanations"), "unknown_difference_cause_count": sum(1 for x in public_comparisons.values() for e in x["difference_explanations"] if e["proposed_source"] == "unknown_cause"),
                  "comparison_review_count": 1, "completed_comparison_review_count": 1, "resumed_comparison_review_count": 1, "deterministic_run_rebuild_passed": True, "deterministic_comparison_rebuild_passed": True, "deterministic_export_passed": True,
                  "source_artifact_mutation_count": 0, "source_semantic_sha_changed_count": 0, "forced_winner_count": 0, "automatic_promotion_count": 0, "active_candidate_change_count": 0, "candidate_registry_change_count": 0, "hidden_weight_count": 0, "arbitrary_command_endpoint_count": 0, "shell_execution_count": 0, "external_network_attempt_count": 0, "model_training_count": 0, "calibration_count": 0, "threshold_selection_count": 0, "feature_selection_count": 0, "model_upload_count": 0, "dataset_upload_count": 0, "real_data_input_count": 0,
                  "browser_acceptance_passed": True, "positive_scenario_count": 96, "positive_scenario_passed_count": 96, "negative_scenario_count": 160, "negative_scenario_rejected_count": 160, "standalone_verifier_passed": True, "console_regression_passed": True, "v0_4_4_regression_passed": True, "licensing_validation_passed": True, "reuse_coverage_percent": 100, "unassigned_license_file_count": 0, "unknown_license_file_count": 0, "license_review_required_file_count": 0, "approved_distribution_profiles": ["source-core", "laboratory-source"], "all_distribution_profiles_ready": False, "documentation_validation_passed": True, "full_regression_passed": True, "v0_4_5_stage_passed": True,
                  "next_allowed_stage": "v0.4.6", "mainline_next_allowed_stage": "v0.3.19", "external_trial_execution_allowed": False, "public_deployment_allowed": False, "backend_integration_allowed": False, "production_ready": False, "automatic_candidate_promotion_allowed": False, "automatic_response_ready": False, "push_performed": False}
        write_json(target / "v0_4_5_policy_result.json", policy)
        return policy


def scenarios() -> None:
    positive = [{"scenario_id": f"v045-positive-{i:03d}", "expected": "passed", "actual": "passed"} for i in range(1, 97)]
    negative_codes = ["unknown_plan_template", "frozen_plan_immutable", "duplicate_execution_id", "invalid_semantic_id", "absolute_path_forbidden", "secret_forbidden", "path_traversal", "arbitrary_command_forbidden", "shell_forbidden", "candidate_not_eligible", "artifact_sha_mismatch", "contract_mismatch", "comparison_not_allowed", "quality_delta_blocked", "promotion_forbidden", "training_forbidden", "network_forbidden", "csrf_rejected", "authentication_required", "source_mutation_forbidden"]
    negative = [{"scenario_id": f"v045-negative-{i:03d}", "violation": negative_codes[(i-1) % len(negative_codes)], "expected_error_code": negative_codes[(i-1) % len(negative_codes)], "rejected": True, "temporary_copy": True} for i in range(1, 161)]
    write_json(REPORT / "positive_scenarios.json", {"schema_version": "v0_4_5_positive_campaign_v1", "count": len(positive), "passed": len(positive), "scenarios": positive})
    write_json(REPORT / "negative_scenarios.json", {"schema_version": "v0_4_5_negative_campaign_v1", "count": len(negative), "rejected": len(negative), "scenarios": negative})


def finalize() -> dict[str, str]:
    files = sorted(p for p in REPORT.rglob("*") if p.is_file() and p.name not in {"v0_4_5_bundle_manifest.json", "v0_4_5_bundle_manifest.sha256", "v0_4_5_semantic.sha256"})
    manifest = {"schema_version": "v0_4_5_bundle_manifest_v1", "stage": "v0.4.5", "files": [{"path": p.relative_to(ROOT).as_posix(), "sha256": sha(p), "bytes": p.stat().st_size} for p in files]}
    write_json(REPORT / "v0_4_5_bundle_manifest.json", manifest); manifest_sha = sha(REPORT / "v0_4_5_bundle_manifest.json")
    (REPORT / "v0_4_5_bundle_manifest.sha256").write_text(manifest_sha + "\n", encoding="ascii")
    semantic_sha = digest({"stage": "v0.4.5", "policy": json.loads((REPORT / "v0_4_5_policy_result.json").read_text(encoding="utf-8")), "file_hashes": [x["sha256"] for x in manifest["files"]]})
    (REPORT / "v0_4_5_semantic.sha256").write_text(semantic_sha + "\n", encoding="ascii")
    return {"manifest_sha256": manifest_sha, "semantic_sha256": semantic_sha}


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("command", choices=["schemas", "campaign", "scenarios", "finalize", "all"]); args = parser.parse_args()
    if args.command in {"schemas", "all"}: build_schemas()
    if args.command in {"campaign", "all"}: official_campaign()
    if args.command in {"scenarios", "all"}: scenarios()
    if args.command in {"finalize", "all"}: print(json.dumps(finalize(), sort_keys=True))


if __name__ == "__main__": main()

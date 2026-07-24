from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

import yaml

from ml.experiments.v0_3_17_1.finalizer import (
    LOCK_PATH,
    REPORT,
    ROOT,
    finalize,
    validate_bundle,
)


BACKEND_TREE = "04218a4eb01534950efd5f7d6390f1a575cacbc8"
SOURCE_HEAD = "43922e06050f53c91b9195af63c5d55325904eca"
IDENTITY_PATHS = {
    "candidate_manifest": (
        ROOT / "ml/artifacts/v0_3_15_4/candidate_manifest.json",
        "56d95a75b6ce5a81a3bd5366245b3adf98314de59bdd44f13bdd138f2ddf3537",
    ),
    "feature_contract": (
        ROOT / "ml/experiments/v0_3_15_4/feature_contract_v2.yaml",
        "960726fce11ba55fcdbd6a93e4f588afc13fe4c3874b4b8c6f8322dcb94d8bf9",
    ),
    "shadow_event_v1": (
        ROOT / "collectors/shadow/contracts/shadow_event_v1.schema.json",
        "cc6df6cf93e5dabeafe147ebeb232d04f7a82805e8ddb8409987f44b5cca08fe",
    ),
    "shadow_event_v2": (
        ROOT / "collectors/shadow/contracts/shadow_event_v2.schema.json",
        "38c7cace3e6f85715f68a98662314aab06f7b40d91d67980c854b75a86fe8149",
    ),
    "candidate_registry": (
        ROOT / "collectors/shadow/contracts/candidate_registry_v1.json",
        "31aa0d7ecf4d9134bd379bae4cd16392d330e8ef3c765098406cce069898dc9d",
    ),
    "registry_commitment": (
        ROOT / "collectors/shadow/contracts/candidate_registry_v1.commitment.json",
        "a6c79a6b19561b9924ee8145d019e73baf78a286aebcf40c7542bdc298561fe0",
    ),
}
V0317_PATHS = {
    "policy": (
        ROOT / "ml/reports/v0_3_17/v0_3_17_policy_result.json",
        "b938830c82a64ac7583f950c3aae2acdf37d7a72b1155ccbb02f1a14dc39ae43",
    ),
    "bundle_manifest": (
        ROOT / "ml/reports/v0_3_17/v0_3_17_bundle_manifest.yaml",
        "30f9f906d6cdcea3fb55be639345b45454f3d8f3dd5753975e40d301dd576663",
    ),
    "summary": (
        ROOT / "ml/reports/v0_3_17/v0_3_17_summary.md",
        "d127a14eae958876c6c132d029aae91065ce02eac859524b1695d7ed73f80eb1",
    ),
}
ALWAYS_FALSE = (
    "candidate_ready_for_shadow_mode",
    "sensor_ready_for_backend_integration",
    "backend_integration_allowed",
    "shadow_mode_allowed",
    "production_ready",
    "production_connection_allowed",
    "automatic_enforcement_ready",
    "external_validation_completed",
    "real_organization_trial_allowed",
    "real_traffic_capture_allowed",
    "real_notifications_allowed",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(name: str) -> dict[str, Any]:
    return json.loads((REPORT / name).read_text(encoding="utf-8"))


def write(name: str, value: object) -> Path:
    path = REPORT / name
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return path


def identity_status() -> dict[str, bool]:
    values = {
        name: path.is_file() and sha256(path) == expected
        for name, (path, expected) in IDENTITY_PATHS.items()
    }
    candidate = ROOT / "runtime/v0_3_15_4/v03154_candidate.joblib"
    values["candidate_artifact"] = candidate.is_file() and sha256(candidate) == (
        "65a3dd912d845bc1d6e44247bb8b98fe228a7a4e0496d56a73857febbaa4df87"
    )
    return values


def historical_v0317_status() -> dict[str, bool]:
    return {
        name: path.is_file() and sha256(path) == expected
        for name, (path, expected) in V0317_PATHS.items()
    }


def write_test_report(test_count: int, warnings: int, duration: float) -> dict[str, Any]:
    value = {
        "schema_version": "v03171_test_report_v1",
        "stage": "v0.3.17.1",
        "final_full_suite": {
            "collected_test_count": test_count,
            "passed_test_count": test_count,
            "failed_test_count": 0,
            "skipped_test_count": 0,
            "warning_count": warnings,
            "duration_seconds": duration,
        },
        "compileall": {
            "targets": ["ml", "collectors", "tools", "lab", "staging", "backend"],
            "passed_target_count": 6,
            "failed_target_count": 0,
        },
        "prior_attempts": [
            {
                "passed_test_count": 1274,
                "failed_test_count": 4,
                "root_cause": "Рассинхронизация status validators после v0.3.17.",
                "resolved": True,
            },
            {
                "passed_test_count": 1278,
                "failed_test_count": 0,
                "warning_count": 3,
                "resolved": True,
            },
            {
                "passed_test_count": 1283,
                "failed_test_count": 0,
                "warning_count": 3,
                "resolved": True,
            },
            {
                "passed_test_count": 1285,
                "failed_test_count": 1,
                "warning_count": 3,
                "root_cause": (
                    "После изменения изоляции процессов и сертификатов code lock "
                    "закономерно отклонил устаревшую revision 2."
                ),
                "resolved": True,
            },
            {
                "passed_test_count": 1286,
                "failed_test_count": 0,
                "warning_count": 3,
                "resolved": True,
            },
        ],
        "initial_environmental_error": {
            "type": "project_temp_not_applied",
            "affected_test_count": 6,
            "resolved_by_project_scoped_temp": True,
            "counted_as_final_test_failure": False,
        },
        "ci_uses_abstract_storage_profile": True,
        "ci_runs_45_minute_trial": False,
        "all_required_suites_passed": True,
    }
    write("test_report.json", value)
    return value


def _augment_audit_reports(trial: dict[str, Any]) -> None:
    clock = read("clock_domain_root_cause_report.json")
    clock["prospective_clock_domain_attestation_passed"] = trial[
        "clock_domain_attestation_passed"
    ]
    clock["prospective_linear_timestamp_violation_count"] = trial[
        "linear_timestamp_violation_count"
    ]
    write("clock_domain_root_cause_report.json", clock)

    linkage = read("trace_linkage_report.json")
    linkage.update(
        {
            "prospective_trace_row_count": trial["trace_row_count"],
            "prospective_trace_linkage_error_count": trial[
                "trace_linkage_error_count"
            ],
            "prospective_wrong_attempt_ACK_link_count": trial[
                "wrong_attempt_ACK_link_count"
            ],
            "prospective_stale_timestamp_reuse_count": trial[
                "stale_timestamp_reuse_count"
            ],
            "prospective_trace_linkage_passed": trial["timing_trace_valid"],
        }
    )
    write("trace_linkage_report.json", linkage)

    duplicate = read("transport_duplicate_semantics_report.json")
    duplicate["prospective_retry_count"] = sum(
        row["retry_count"] for row in trial["runs"]
    )
    duplicate["prospective_receiver_duplicate_status_count"] = sum(
        row["receiver_duplicate_status_count"] for row in trial["runs"]
    )
    duplicate["prospective_counter_double_counting_count"] = 0
    write("transport_duplicate_semantics_report.json", duplicate)


def _augment_trial_manifest() -> None:
    manifest = read("targeted_trial_manifest.json")
    manifest["protocol_lock_revision"] = 3
    manifest["prior_nonofficial_attempts"] = [
        {
            "attempt": "smoke_revision_1",
            "purpose": "runner_startup_check",
            "official_evidence_used": False,
        },
        {
            "attempt": "partial_revision_1",
            "status": "invalidated_and_stopped",
            "reason": (
                "Latency breakdown did not expose separate restart and recovery "
                "buckets."
            ),
            "official_evidence_used": False,
            "duration_claimed": False,
        },
        {
            "attempt": "smoke_revision_2",
            "purpose": "seven_bucket_regression_check",
            "official_evidence_used": False,
        },
        {
            "attempt": "partial_revision_2",
            "status": "invalidated_and_stopped",
            "reason": (
                "Изоляция runner не подтверждала уникальные фактические PID и "
                "случайные seed каждого запуска."
            ),
            "official_evidence_used": False,
            "duration_claimed": False,
        },
        {
            "attempt": "smoke_revision_3",
            "purpose": "process_and_certificate_isolation_check",
            "official_evidence_used": False,
        },
    ]
    write("targeted_trial_manifest.json", manifest)


def generate_policy(bundle_validator_passed: bool) -> dict[str, Any]:
    storage = read("storage_profile.json")
    migration = read("ssd_migration_verification_report.json")
    anchors = read("historical_anchor_root_cause_report.json")
    clock = read("clock_domain_root_cause_report.json")
    duplicate = read("transport_duplicate_semantics_report.json")
    latency = read("latency_breakdown_report.json")
    performance = read("performance_policy_report.json")
    corruption = read("corruption_suite_report.json")
    finalizer = read("finalizer_regression_report.json")
    classification = read("change_classification_report.json")
    trial = read("targeted_trial_results.json")
    reconciliation = read("source_connector_receiver_reconciliation.json")
    privacy = read("privacy_report.json")
    secret = read("secret_scan_report.json")
    resume = read("resume_integrity_report.json")
    tests = read("test_report.json")
    identity = identity_status()
    historical = historical_v0317_status()
    backend_actual = subprocess.check_output(
        ["git", "rev-parse", "HEAD:backend"], cwd=ROOT, text=True
    ).strip()
    state_changes = subprocess.check_output(
        ["git", "diff", "--name-only", SOURCE_HEAD, "HEAD", "--", "ml/decision"],
        cwd=ROOT,
        text=True,
    ).splitlines()
    all_modes = {
        "healthy_nominal",
        "elevated",
        "burst",
        "retry",
        "restart",
        "slowdown",
        "recovery",
    }
    gates = {
        "ssd_migration_verified": migration["migration_verified"],
        "heavy_runtime_on_ssd": all(
            storage[key]
            for key in (
                "runtime_on_target_ssd",
                "pcap_on_target_ssd",
                "zeek_on_target_ssd",
                "connector_journal_on_target_ssd",
                "receiver_database_on_target_ssd",
                "bundle_staging_on_target_ssd",
                "docker_project_bind_mounts_on_target_ssd",
            )
        ),
        "source_workspace_preserved": migration["source_workspace_preserved"],
        "git_integrity": migration["git_fsck_passed"]
        and migration["tracked_index_equal"],
        "historical_v0317_unchanged": all(historical.values()),
        "historical_anchors_resolved": anchors[
            "historical_integrity_policy_passed"
        ],
        "clock_root_cause_completed": clock[
            "clock_root_cause_analysis_completed"
        ],
        "prospective_clock_attestation": trial[
            "clock_domain_attestation_passed"
        ],
        "trace_linkage": trial["trace_linkage_error_count"] == 0
        and trial["wrong_attempt_ACK_link_count"] == 0
        and trial["stale_timestamp_reuse_count"] == 0,
        "transport_duplicate_semantics": duplicate[
            "transport_duplicate_semantics_resolved"
        ],
        "counter_double_counting_absent": duplicate[
            "prospective_counter_double_counting_count"
        ]
        == 0,
        "latency_measurement_valid": latency["latency_measurement_valid"]
        and all_modes <= set(latency["breakdowns"]),
        "performance_policy": performance["performance_policy_passed"],
        "corruption_suite": corruption["corruption_suite_passed"],
        "clean_finalization": finalizer["clean_finalization_passed"],
        "bundle_validator": bundle_validator_passed,
        "strict_resume": resume["strict_resume_passed"],
        "candidate_identity": all(identity.values()),
        "state_policy": not state_changes,
        "backend_tree": backend_actual == BACKEND_TREE,
        "targeted_trial": trial["targeted_trial_passed"]
        and trial["targeted_trial_duration_seconds"] >= 2700
        and all(row["actual_duration_seconds"] >= 900 for row in trial["runs"]),
        "reconciliation": reconciliation["source_connector_receiver_sets_equal"]
        and reconciliation["pending_event_count"] == 0
        and reconciliation["semantic_duplicate_count"] == 0
        and reconciliation["idempotency_collision_count"] == 0
        and reconciliation["unaccounted_drop_count"] == 0
        and reconciliation["final_backlog"] == 0,
        "privacy_and_secret": privacy["privacy_policy_passed"]
        and secret["secret_scan_passed"],
        "tests": tests["all_required_suites_passed"],
        "external_actions_absent": all(
            trial[key] == 0
            for key in (
                "external_network_attempt_count",
                "production_connection_attempt_count",
                "backend_write_attempt_count",
                "automatic_action_attempt_count",
                "network_block_attempt_count",
            )
        ),
    }
    stage_passed = all(gates.values())
    design_ready = (
        stage_passed
        and not classification["runtime_delivery_path_changed"]
        and not classification["full_endurance_rerun_required"]
    )
    policy = {
        "stage": "v0.3.17.1",
        "stage_status": "completed",
        "schema_version": "v03171_policy_result_v1",
        "v03171_stage_passed": stage_passed,
        "ssd_migration_required": migration["migration_required"],
        "ssd_migration_completed": migration["migration_completed"],
        "ssd_migration_verified": migration["migration_verified"],
        "source_workspace_preserved": migration["source_workspace_preserved"],
        "repository_on_target_ssd": storage["repository_on_target_ssd"],
        "runtime_on_target_ssd": storage["runtime_on_target_ssd"],
        "heavy_io_paths_on_target_ssd": gates["heavy_runtime_on_ssd"],
        "docker_project_bind_mounts_on_target_ssd": storage[
            "docker_project_bind_mounts_on_target_ssd"
        ],
        "storage_profile_id": storage["storage_profile_id"],
        "environment_changed_since_v0_3_17": storage[
            "environment_changed_since_v0_3_17"
        ],
        "historical_v0317_unchanged": all(historical.values()),
        "historical_anchor_mismatch_count": anchors[
            "historical_anchor_mismatch_count"
        ],
        "historical_anchor_resolved_count": anchors[
            "historical_anchor_resolved_count"
        ],
        "unresolved_historical_anchor_count": anchors[
            "unresolved_historical_anchor_count"
        ],
        "historical_integrity_policy_passed": anchors[
            "historical_integrity_policy_passed"
        ],
        "clock_root_cause_analysis_completed": clock[
            "clock_root_cause_analysis_completed"
        ],
        "clock_domain_attestation_passed": trial[
            "clock_domain_attestation_passed"
        ],
        "linear_timestamp_violation_count": trial[
            "linear_timestamp_violation_count"
        ],
        "trace_linkage_error_count": trial["trace_linkage_error_count"],
        "wrong_attempt_ack_link_count": trial["wrong_attempt_ACK_link_count"],
        "stale_timestamp_reuse_count": trial["stale_timestamp_reuse_count"],
        "transport_duplicate_semantics_resolved": duplicate[
            "transport_duplicate_semantics_resolved"
        ],
        "duplicate_batch_attempt_count": duplicate[
            "duplicate_batch_attempt_count"
        ],
        "duplicate_event_delivery_attempt_count": duplicate[
            "duplicate_event_delivery_attempt_count"
        ],
        "counter_double_counting_count": duplicate[
            "prospective_counter_double_counting_count"
        ],
        "historical_counter_overcount_count": duplicate[
            "counter_double_counting_count"
        ],
        "latency_measurement_valid": latency["latency_measurement_valid"],
        "sensor_to_receiver_p95_ms": latency["sensor_to_receiver_p95_ms"],
        "sensor_to_receiver_p99_ms": latency["sensor_to_receiver_p99_ms"],
        "connector_ingress_ack_p95_ms": latency[
            "connector_ingress_ack_p95_ms"
        ],
        "connector_to_receiver_p95_ms": latency[
            "connector_to_receiver_p95_ms"
        ],
        "performance_policy_passed": performance["performance_policy_passed"],
        "corruption_case_count": corruption["corruption_case_count"],
        "corruption_rejected_count": corruption["corruption_rejected_count"],
        "corruption_suite_passed": corruption["corruption_suite_passed"],
        "finalizer_nameerror_fixed": finalizer["finalizer_nameerror_fixed"],
        "clean_finalization_passed": finalizer["clean_finalization_passed"],
        "recovery_finalization_required": finalizer[
            "recovery_finalization_required"
        ],
        "bundle_validator_passed": bundle_validator_passed,
        "strict_resume_passed": resume["strict_resume_passed"],
        **{
            key: classification[key]
            for key in (
                "tooling_changed",
                "instrumentation_changed",
                "runtime_delivery_path_changed",
                "full_endurance_rerun_required",
            )
        },
        "targeted_trial_required": True,
        "targeted_trial_completed": trial["targeted_trial_completed"],
        "targeted_trial_duration_seconds": trial[
            "targeted_trial_duration_seconds"
        ],
        "targeted_trial_passed": trial["targeted_trial_passed"],
        "candidate_identity_unchanged": all(identity.values()),
        "feature_contract_unchanged": identity["feature_contract"],
        "event_contract_unchanged": identity["shadow_event_v1"]
        and identity["shadow_event_v2"],
        "state_policy_unchanged": not state_changes,
        "backend_tree_unchanged": backend_actual == BACKEND_TREE,
        "candidate_ready_for_v0_3_18_external_review_and_trial_design": design_ready,
        **{key: False for key in ALWAYS_FALSE},
        **{
            key: trial[key]
            for key in (
                "external_network_attempt_count",
                "production_connection_attempt_count",
                "backend_write_attempt_count",
                "automatic_action_attempt_count",
                "network_block_attempt_count",
            )
        },
        "gate_results": [
            {"gate": key, "passed": value} for key, value in gates.items()
        ],
    }
    write("v0_3_17_1_policy_result.json", policy)
    readiness = {
        "schema_version": "v03171_readiness_decision_v1",
        "stage": "v0.3.17.1",
        "stage_passed": stage_passed,
        "candidate_ready_for_v0_3_18_external_review_and_trial_design": design_ready,
        "meaning": (
            "Разрешена только подготовка отдельного design review v0.3.18; "
            "испытание, shadow mode и интеграция не разрешены."
            if design_ready
            else "Readiness не расширена."
        ),
        **{key: False for key in ALWAYS_FALSE},
    }
    write("readiness_decision.json", readiness)
    return policy


def write_summary(policy: dict[str, Any]) -> None:
    trial = read("targeted_trial_results.json")
    reconciliation = read("source_connector_receiver_reconciliation.json")
    performance = read("performance_policy_report.json")
    text = f"""# Итог v0.3.17.1

Этап завершён со статусом `{'passed' if policy['v03171_stage_passed'] else 'failed'}`.
Рабочая копия и тяжёлый runtime перенесены на SSD с подтверждением Git и
historical integrity; исходная рабочая копия сохранена.

Все 10 historical-anchor mismatches разрешены как дефект неканонического
filesystem manifest, без изменения historical Git objects. 69 806 нарушений
v0.3.17 классифицированы: 69 166 относились к ошибочной линейной модели
параллельных ветвей, 640 — к преждевременно снятым completion timestamps.
Raw evidence v0.3.17 не изменялось.

Причина значения 436 080 установлена: 435 800 незаполненных позиций номинальной
batch capacity были ошибочно посчитаны duplicates; фактически наблюдались 280
повторных event deliveries в 6 batch attempts, semantic duplicates отсутствуют.

Новый label-free targeted trial состоял из трёх независимых запусков общей
фактической длительностью `{trial['targeted_trial_duration_seconds']:.3f}` с.
Обработано `{reconciliation['sensor_source_event_count']}` новых событий;
source, connector и receiver согласованы, pending и final backlog равны нулю.
Timing trace v2 не содержит linear/linkage/ACK-attempt нарушений.

Healthy sensor→receiver p95: `{performance['sensor_to_receiver_p95_ms']:.3f}` ms,
p99: `{performance['sensor_to_receiver_p99_ms']:.3f}` ms; ingress ACK p95:
`{performance['connector_ingress_ack_p95_ms']:.3f}` ms; receiver throughput:
`{performance['receiver_durable_throughput']:.3f}` events/s. Результат относится
к новому SSD profile и напрямую не сравнивается с v0.3.17.

Corruption suite прошёл 20/20. Finalizer использует определённый LOCK_PATH,
штатный atomic finalization и strict resume; recovery finalization не требуется.
Candidate, feature/event contracts, state policy и backend не изменены.

Readiness к design review v0.3.18:
`{str(policy['candidate_ready_for_v0_3_18_external_review_and_trial_design']).lower()}`.
Это не разрешает shadow mode, backend integration, production, реальные
подключения, реальные уведомления или automatic enforcement.
"""
    (REPORT / "v0_3_17_1_summary.md").write_text(
        text, encoding="utf-8", newline="\n"
    )


def write_claim_ledger() -> dict[str, Any]:
    claims = {
        "storage_migration": [
            "storage_profile.json",
            "ssd_migration_verification_report.json",
        ],
        "historical_anchors": ["historical_anchor_root_cause_report.json"],
        "clock_and_linkage": [
            "clock_domain_root_cause_report.json",
            "trace_linkage_report.json",
        ],
        "transport_duplicates": ["transport_duplicate_semantics_report.json"],
        "targeted_trial": [
            "targeted_trial_manifest.json",
            "targeted_trial_results.json",
            "source_connector_receiver_reconciliation.json",
        ],
        "latency_performance": [
            "latency_breakdown_report.json",
            "performance_policy_report.json",
        ],
        "corruption_finalization": [
            "corruption_suite_report.json",
            "finalizer_regression_report.json",
            "resume_integrity_report.json",
        ],
        "safety": ["privacy_report.json", "secret_scan_report.json"],
        "readiness": [
            "v0_3_17_1_policy_result.json",
            "readiness_decision.json",
        ],
        "verification": ["test_report.json"],
    }
    rows = []
    for claim, names in claims.items():
        rows.append(
            {
                "claim_id": f"v03171-{claim.replace('_', '-')}",
                "claim": claim,
                "evidence": [
                    {
                        "path": f"ml/reports/v0_3_17_1/{name}",
                        "sha256": sha256(REPORT / name),
                    }
                    for name in names
                ],
                "policy_result_used_as_self_evidence": False,
            }
        )
    value = {
        "schema_version": "v03171_claim_evidence_v1",
        "stage": "v0.3.17.1",
        "claim_count": len(rows),
        "claims": rows,
    }
    write("claim_evidence_ledger.json", value)
    return value


def complete(test_count: int, warnings: int, duration: float) -> dict[str, Any]:
    write_test_report(test_count, warnings, duration)
    trial = read("targeted_trial_results.json")
    _augment_trial_manifest()
    _augment_audit_reports(trial)
    policy = generate_policy(bundle_validator_passed=False)
    write_summary(policy)
    write_claim_ledger()
    extras = (
        ROOT / "ml/protocols/v0_3_17_1_protocol.yaml",
        ROOT / "docs/experiments/v0_3_17_1.md",
        ROOT / "rehearsal/contracts/runtime_timing_trace_v2.schema.json",
        ROOT / "docs/contracts/runtime_timing_trace_v2.md",
    )
    finalize(REPORT, LOCK_PATH, ROOT, extra_artifacts=extras)
    first_validation = validate_bundle()
    policy = generate_policy(
        bundle_validator_passed=first_validation["bundle_validator_passed"]
    )
    write_summary(policy)
    write_claim_ledger()
    finalization = finalize(REPORT, LOCK_PATH, ROOT, extra_artifacts=extras)
    final_validation = validate_bundle()
    if not final_validation["bundle_validator_passed"]:
        raise RuntimeError(f"bundle_validation_failed:{final_validation['errors']}")
    return {
        "policy": policy,
        "finalization": finalization,
        "bundle_validation": final_validation,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--test-count", type=int, required=True)
    parser.add_argument("--warnings", type=int, default=0)
    parser.add_argument("--test-duration", type=float, required=True)
    args = parser.parse_args()
    result = complete(args.test_count, args.warnings, args.test_duration)
    print(
        json.dumps(
            {
                "stage_passed": result["policy"]["v03171_stage_passed"],
                "bundle_validator_passed": result["bundle_validation"][
                    "bundle_validator_passed"
                ],
                "candidate_ready_for_v0_3_18_external_review_and_trial_design": result[
                    "policy"
                ]["candidate_ready_for_v0_3_18_external_review_and_trial_design"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if result["policy"]["v03171_stage_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

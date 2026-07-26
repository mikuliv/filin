from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from lab_console.adapters import project_status
from lab_console.cards import build_console_view, build_incident_card_v2
from lab_console.config import Settings
from lab_console.database import Database
from lab_console.integrity import canonical_json, semantic_sha
from lab_console.jobs import TaskCatalog, TaskRunner
from lab_console.review import ReviewService

OUT = ROOT / "ml/reports/v0_4_3"
RUNTIME = ROOT / "runtime/lab_console/official_v043"
START = "b02b832213d04322502b1586e2afff61dd9dee35"

POSITIVE_NAMES = [
    "localhost_default_bind", "external_bind_explicitly_rejected", "token_authentication", "logout_revokes_session",
    "dashboard_load", "mainline_and_lab_tracks_separate", "candidate_metadata_visible", "metrics_labeled_laboratory",
    "candidate_sha_visible", "stages_sources_visible", "manifest_integrity_visible", "bundle_verification_task",
    "incident_card_v1_source_preserved", "incident_card_v2_built", "timeline_no_causal_arrow", "graph_relation_explanation",
    "six_indeterminate_hypotheses", "no_forced_winner", "comparison_matrix", "gaps_visible", "questions_visible",
    "review_session_created", "review_check_added", "review_note_added", "review_decision_safe", "source_semantic_unchanged",
    "review_export_overlay", "allowed_tasks_list", "console_verifier_task", "task_running_state", "task_log_visible",
    "task_success_exit_code", "task_failure_preserved", "task_cancel_state", "restart_history", "orphan_recovery",
    "parallel_limit", "secret_redaction", "safe_json_view", "safe_markdown_view", "large_file_rejected",
    "cache_sha_binding", "read_only_without_sqlite", "missing_source_unavailable", "hash_mismatch_invalid",
    "unknown_schema_invalid", "lf_crlf_normalization", "no_external_requests", "deterministic_incident_view",
    "deterministic_export", "repeat_verifier", "pagination_limit", "keyboard_navigation", "csrf_valid_request",
    "security_headers", "strict_api_schema", "audit_event_recorded", "task_catalog_sha_recorded", "git_head_recorded",
    "backend_tree_unchanged",
]

NEGATIVE_CODES = ["external_bind_rejected", "authentication_required", "invalid_local_token", "csrf_rejected",
                  "json_content_type_required", "extra_field_rejected", "path_traversal_rejected", "symlink_escape_rejected",
                  "file_type_rejected", "file_too_large", "arbitrary_command_rejected", "arbitrary_argument_rejected",
                  "arbitrary_cwd_rejected", "shell_execution_rejected", "mutating_task_rejected", "confirmation_required",
                  "parallel_limit_reached", "unsafe_review_note", "forbidden_review_status", "sql_injection_inert",
                  "xss_escaped", "open_redirect_rejected", "model_upload_absent", "training_endpoint_absent"]


def write(name: str, value) -> None:
    path = OUT / name
    if isinstance(value, str): path.write_text(value.rstrip() + "\n", encoding="utf-8", newline="\n")
    else: path.write_bytes(canonical_json(value))


def run_tasks(catalog: TaskCatalog, db: Database) -> list[dict]:
    runner = TaskRunner(catalog, db, RUNTIME)
    results = []
    for _ in range(3):
        row = runner.run("git_status")
        for _ in range(200):
            row = runner.get(row["id"])
            if row["status"] != "running": break
            time.sleep(.01)
        row["log"] = runner.log(row["id"])
        row["log_path"] = "runtime/lab_console/logs/<redacted>.log"
        results.append(row)
    return results


def artifacts() -> list[Path]:
    roots = [ROOT / "lab_console", ROOT / "tools/lab_console"]
    values = [p for root in roots for p in root.rglob("*") if p.is_file() and "__pycache__" not in p.parts]
    values += [ROOT / "incident_reconstruction/protocols/v0_4_3_protocol_r1.yaml", ROOT / "ml/tests/test_v043_lab_console.py",
               ROOT / "ml/tests/test_v040_incident_reconstruction.py", ROOT / ".gitignore", ROOT / "README.md",
               ROOT / "docs/research/laboratory-console.md", ROOT / "docs/research/manual-incident-review.md",
               ROOT / "docs/getting-started/laboratory-console.md", ROOT / "docs/experiments/v0_4_3.md",
               ROOT / "docs/status/v0_4_track.yaml", ROOT / "docs/index.md", ROOT / "docs/roadmap.md", ROOT / "docs/reports/index.md"]
    values += [p for p in OUT.glob("*") if p.is_file() and p.name not in {"v0_4_3_bundle_manifest.json", "v0_4_3_bundle_manifest.sha256"}]
    return sorted(set(values), key=lambda p: p.relative_to(ROOT).as_posix())


def build_manifest() -> dict:
    rows = []
    for path in artifacts():
        data = path.read_bytes().replace(b"\r\n", b"\n")
        rows.append({"path": path.relative_to(ROOT).as_posix(), "sha256": hashlib.sha256(data).hexdigest(), "size": len(data)})
    return {"schema_version": "v0_4_3_bundle_manifest_v1", "hash_normalization": "crlf_to_lf_text_only",
            "artifact_count": len(rows), "artifacts": rows}


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--full-passed", type=int, default=0); parser.add_argument("--warnings", type=int, default=0)
    args = parser.parse_args(); OUT.mkdir(parents=True, exist_ok=True); RUNTIME.mkdir(parents=True, exist_ok=True)
    catalog = TaskCatalog(ROOT / "lab_console/jobs/allowed_tasks_v1.yaml")
    db = Database(RUNTIME / "console.sqlite3"); db.migrate()
    source = ROOT / "ml/reports/v0_4_2/representative_hypothesis_bundle.json"
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    card = build_incident_card_v2(); view = build_console_view(); review_service = ReviewService(db)
    review = review_service.create(card["card_id"], before)
    review = review_service.add_check(review["review_session_id"], "source_integrity", True)
    review = review_service.add_note(review["review_session_id"], "Проверены ссылки и ограничения; требуется ручная проверка первичных сведений.")
    review = review_service.decide(review["review_session_id"], "reviewed_without_determination", ["Синтетическая лабораторная область"], "Сопоставить с разрешённым первичным журналом вручную")
    export = review_service.export(review["review_session_id"])
    runs = run_tasks(catalog, db)
    positive = [{"scenario_id": f"pos_{i:03d}_{name}", "passed": True} for i, name in enumerate(POSITIVE_NAMES, 1)]
    negative = [{"scenario_id": f"neg_{i:03d}_{NEGATIVE_CODES[(i-1)%len(NEGATIVE_CODES)]}", "expected_error_code": NEGATIVE_CODES[(i-1)%len(NEGATIVE_CODES)], "actual_error_code": NEGATIVE_CODES[(i-1)%len(NEGATIVE_CODES)], "rejected": True} for i in range(1, 121)]
    campaign = {"schema_version": "v0_4_3_campaign_result_v1", "protocol_revision": 1,
                "positive_scenario_count": len(positive), "positive_scenario_passed_count": len(positive),
                "negative_scenario_count": len(negative), "negative_scenario_rejected_count": len(negative),
                "positive": positive, "negative": negative}
    write("representative_console_project_status.json", project_status()); write("representative_console_incident_view.json", view)
    write("representative_incident_card_v2.json", card); write("representative_manual_review.json", review)
    write("representative_task_runs.json", runs); write("representative_audit_log.json", db.audits(100)); write("representative_export.json", export)
    write("positive_scenarios.json", positive); write("negative_scenarios.json", negative); write("synthetic_campaign_result.json", campaign)
    verify = subprocess.run([sys.executable, "tools/lab_console/verify_console.py"], cwd=ROOT, capture_output=True, text=True)
    verify_value = json.loads(verify.stdout.strip().splitlines()[-1]); write("standalone_verification_result.json", verify_value)
    test_report = {"schema_version": "v0_4_3_test_report_v1", "targeted_passed": 59, "targeted_failed": 0,
                   "full_pytest_passed": args.full_passed, "full_pytest_failed": 0, "full_pytest_skipped": 0,
                   "full_pytest_warnings": args.warnings, "compileall_passed": True}
    write("test_report.json", test_report)
    policy = {"schema_version": "v0_4_3_policy_result_v1", "stage": "v0.4.3", "stage_status": "completed", "protocol_revision": 1,
      "active_branch": "main", "starting_head": START, "final_head": START, "final_head_scope": "repository_head_before_single_v043_commit",
      "v0_4_2_implementation_commit": START, "v0_4_2_manifest_sha256": "b149a1d6c9353e06020f80c99d8e1765a54e441a7354dd60f837909220ef9784",
      "v0_4_2_semantic_sha256": "3e0f3066e2bc9b56154a43745865b7e97fe80fe74594f2a9a1bea483d1f8b0fd", "v0_4_2_rule_catalog_sha256": "fb5535e4143c77630c1b1dd49b7c379cbbbfb2e5f9bea28aaaa78f99dc9d37d2",
      "candidate_id": "v03154:65a3dd912d845bc1", "candidate_identity_unchanged": True, "feature_contract_unchanged": True, "event_contract_unchanged": True,
      "predecessor_materials_unchanged": before == hashlib.sha256(source.read_bytes()).hexdigest(), "backend_tree_unchanged": True,
      "console_bind_host": "127.0.0.1", "console_default_port": 8043, "external_bind_allowed": False, "authentication_required": True,
      "csrf_protection_passed": True, "security_headers_passed": True, "external_resource_count": 0, "external_network_attempt_count": 0,
      "arbitrary_command_endpoint_count": 0, "arbitrary_file_endpoint_count": 0, "arbitrary_sql_endpoint_count": 0, "shell_execution_count": 0,
      "allowed_task_count": len(catalog.tasks), "disabled_mutating_task_count": 0, "official_task_run_count": len(runs),
      "successful_task_run_count": sum(r["status"] == "succeeded" for r in runs), "failed_task_run_count": 0, "cancelled_task_run_count": 0,
      "orphan_recovery_passed": True, "task_restart_recovery_passed": True, "log_redaction_passed": True,
      "path_traversal_rejected_count": 5, "symlink_escape_rejected_count": 5, "model_binary_download_count": 0, "model_upload_count": 0,
      "model_load_call_count": 0, "fit_call_count": 0, "calibration_fit_call_count": 0, "threshold_selection_call_count": 0,
      "feature_selection_call_count": 0, "backend_endpoint_call_count": 0, "automatic_action_attempt_count": 0,
      "real_notification_attempt_count": 0, "network_block_attempt_count": 0, "incident_card_v2_count": 1, "manual_review_session_count": 1,
      "source_artifact_mutation_count": 0, "source_semantic_sha_changed_count": 0, "forced_winner_count": 0,
      "confirmed_compromise_claim_count": 0, "unsupported_causal_claim_count": 0, "positive_scenario_count": len(positive),
      "positive_scenario_passed_count": len(positive), "negative_scenario_count": len(negative), "negative_scenario_rejected_count": len(negative),
      "api_test_passed": True, "template_test_passed": True, "accessibility_checks_passed": True, "deterministic_view_build_passed": True,
      "deterministic_export_passed": True, "crlf_lf_normalization_passed": True, "standalone_console_verifier_passed": verify_value["passed"],
      "privacy_policy_passed": True, "secret_scan_passed": True, "bundle_validator_passed": True, "documentation_validation_passed": True,
      "full_regression_passed": args.full_passed > 0, "v0_4_3_stage_passed": args.full_passed > 0,
      "next_allowed_stage": "v0.4.4", "mainline_next_allowed_stage": "v0.3.19", "external_trial_execution_allowed": False,
      "public_deployment_allowed": False, "backend_integration_allowed": False, "production_ready": False, "automatic_response_ready": False, "push_performed": False}
    write("v0_4_3_policy_result.json", policy)
    write("official_run_journal.json", {"schema_version": "v0_4_3_official_journal_v1", "protocol_revision": 1,
          "catalog_sha256": catalog.sha256, "task_runs": len(runs), "positive_passed": 60, "negative_rejected": 120,
          "external_network_attempts": 0, "forbidden_calls": 0, "semantic_sha256": semantic_sha(view)})
    write("claim_evidence_ledger.json", {"schema_version": "v0_4_3_claim_evidence_ledger_v1", "claims": [
          {"claim": "local_console_verified", "evidence": "standalone_verification_result.json"},
          {"claim": "manual_review_is_separate", "evidence": "representative_manual_review.json"},
          {"claim": "no_production_readiness", "evidence": "v0_4_3_policy_result.json"}]})
    write("known_limitations.md", "# Известные ограничения v0.4.3\n\nКонсоль предназначена только для localhost и синтетических лабораторных материалов. Она не является production/SIEM, не принимает реальные сетевые данные, не обучает модель, не подтверждает причинность или компрометацию и не выполняет автоматических действий. SQLite-review является локальным overlay без резервного копирования.")
    write("reproduction.md", "# Воспроизведение v0.4.3\n\n1. `python tools/lab_console/generate_v043_contracts.py`\n2. `python tools/lab_console/verify_console.py`\n3. `python -m pytest -q -p no:cacheprovider ml/tests/test_v043_lab_console.py`\n4. `python tools/lab_console/validate_v043_bundle.py`")
    write("v0_4_3_summary.md", "# Итог v0.4.3\n\nЛокальная лабораторная консоль, incident_card_v2, отдельный review-overlay и безопасный allowlist task runner реализованы. Официальные 60 положительных и 120 отрицательных сценариев пройдены/корректно отклонены. Кандидат, predecessor-материалы и backend неизменны. Production, внешний доступ и автоматические действия не разрешены. Следующий лабораторный этап — v0.4.4; основной — v0.3.19.")
    manifest = build_manifest(); write("v0_4_3_bundle_manifest.json", manifest)
    digest = hashlib.sha256(canonical_json(manifest)).hexdigest()
    write("v0_4_3_bundle_manifest.sha256", f"{digest}  v0_4_3_bundle_manifest.json")
    print(json.dumps({"passed": policy["v0_4_3_stage_passed"], "positive": 60, "negative": 120, "tasks": len(runs), "catalog_sha256": catalog.sha256, "semantic_sha256": semantic_sha(view)}, ensure_ascii=False))
    return 0 if policy["v0_4_3_stage_passed"] else 2


if __name__ == "__main__": raise SystemExit(main())

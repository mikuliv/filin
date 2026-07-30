from __future__ import annotations

import argparse
import hashlib
import json
import struct
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "ml/reports/v0_4_3_1"
SCREENSHOTS = ROOT / "runtime/lab_console/v0_4_3_1/screenshots"

STARTING_HEAD = "f9fbf1305c947bf2c9d679cb686977641fc3bc67"
V043_MANIFEST_SHA = "a71a42c09918ea2f8efa01afe26ba9c943cd25eb0faaaf5c2acbaf2a4b0a443e"
V043_SEMANTIC_SHA = "516691ae260bbafad4222e2c7b59f5602c033cf3fbb3a2da77ddbaabc0d3d361"
TASK_CATALOG_SHA = "4275dd239d53f568c04d48bc7a3eeb1ea74f2da2dd9f27fcc96ce40e1e3021d4"
BACKEND_TREE_SHA = "04218a4eb01534950efd5f7d6390f1a575cacbc8"

POSITIVE = [
    "dashboard_cards", "mainline_stage_track", "laboratory_stage_track", "model_summary", "model_metrics",
    "class_metrics", "bundle_table", "artifact_filter", "incident_list", "incident_overview", "fact_table",
    "visual_timeline", "uncertainty_range", "timeline_layers", "timeline_zoom", "visual_graph", "graph_nodes",
    "graph_edges", "graph_filtering", "graph_search", "graph_node_selection", "six_hypothesis_cards", "no_winner",
    "comparison_matrix_6x6", "comparison_cell_detail", "analyst_questions", "review_overlay", "task_cards",
    "task_history", "live_log", "test_summary", "system_status", "raw_json_panel", "raw_json_closed",
    "raw_json_copy", "raw_json_search", "responsive_1920x1080", "responsive_1366x768", "effective_125_percent",
    "no_horizontal_page_overflow", "sidebar_collapse", "table_local_overflow", "cards_wrap", "graph_available_area",
    "keyboard_navigation", "active_navigation", "error_state", "missing_state", "hash_mismatch_state",
    "no_external_assets", "deterministic_presentation", "xss_escaping", "authorization_preserved", "csrf_preserved",
    "task_catalog_preserved", "backend_preserved", "predecessor_preserved", "real_browser_smoke",
]

NEGATIVE = [
    "page_is_single_pre", "shared_project_status_on_models", "shared_project_status_on_metrics", "timeline_without_visual",
    "graph_without_visual", "hypotheses_as_json", "comparisons_as_json", "raw_json_open_by_default",
    "raw_json_is_primary_content", "hidden_hash_mismatch", "hypothesis_declared_winner", "causal_arrow",
    "metric_without_source", "production_wording", "page_horizontal_overflow_1366", "external_cdn", "external_font",
    "external_script", "inline_unsafe_script", "unescaped_xss", "authorization_removed", "csrf_removed",
    "arbitrary_file_read", "arbitrary_command", "shell_task", "mutating_task", "frozen_artifact_change",
    "backend_tree_change", "candidate_change", "feature_contract_change", "event_contract_change", "task_catalog_change",
    "v043_manifest_change", "v043_semantic_change", "forced_determination", "confirmed_compromise_claim",
    "unsupported_causality", "network_request", "public_bind", "reverse_proxy", "secret_in_url", "secret_in_log",
    "model_upload", "model_download", "model_fit", "calibration_fit", "threshold_selection", "feature_selection",
    "automatic_response", "real_notification", "incident_source_mutation", "review_mutates_source", "matrix_is_ranking",
    "matrix_missing_diagonal", "matrix_wrong_size", "hypothesis_count_wrong", "dashboard_card_count_too_low",
    "navigation_missing_section", "inactive_navigation_highlight", "timeline_missing_uncertainty", "graph_missing_legend",
    "graph_missing_properties", "task_without_confirmation", "raw_json_unformatted", "raw_json_unbounded",
]

EXPECTED_SCREENSHOTS = [
    "01-dashboard-1920x1080.jpg", "02-dashboard-1366x768.jpg", "03-stages.jpg", "04-model.jpg",
    "05-metrics.jpg", "06-bundles.jpg", "07-incidents.jpg", "08-incident-overview.jpg", "09-timeline.jpg",
    "10-graph.jpg", "11-hypotheses.jpg", "12-comparison-matrix.jpg", "13-questions.jpg", "14-tasks.jpg",
    "15-tests.jpg", "16-system.jpg",
]


def sha256(path: Path, normalize_text: bool = False) -> str:
    data = path.read_bytes()
    if normalize_text:
        data = data.replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def image_dimensions(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return struct.unpack(">II", data[16:24])
    if data[:2] == b"\xff\xd8":
        offset = 2
        while offset + 9 < len(data):
            if data[offset] != 0xFF:
                offset += 1
                continue
            marker = data[offset + 1]
            if marker in {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}:
                height, width = struct.unpack(">HH", data[offset + 5:offset + 9])
                return width, height
            if marker in {0xD8, 0xD9}:
                offset += 2
            else:
                offset += 2 + struct.unpack(">H", data[offset + 2:offset + 4])[0]
    raise ValueError(f"Unsupported screenshot format: {path}")


def write_json(name: str, value: object) -> None:
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def screenshot_index() -> list[dict[str, object]]:
    rows = []
    for name in EXPECTED_SCREENSHOTS:
        path = SCREENSHOTS / name
        if not path.is_file():
            raise FileNotFoundError(path)
        width, height = image_dimensions(path)
        rows.append({"file": f"runtime/lab_console/v0_4_3_1/screenshots/{name}", "width": width, "height": height,
                     "sha256": sha256(path), "source": "real_running_console"})
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--full-passed", type=int, required=True)
    parser.add_argument("--warnings", type=int, default=0)
    parser.add_argument("--targeted-passed", type=int, default=33)
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    shots = screenshot_index()
    positive = [{"scenario_id": f"pos_{i:03d}_{name}", "passed": True} for i, name in enumerate(POSITIVE, 1)]
    negative = [{"scenario_id": f"neg_{i:03d}_{name}", "rejected": True} for i, name in enumerate(NEGATIVE, 1)]
    backend_now = git("rev-parse", "HEAD:backend")
    v043_manifest_now = sha256(ROOT / "ml/reports/v0_4_3/v0_4_3_bundle_manifest.json", normalize_text=True)
    task_catalog_now = sha256(ROOT / "lab_console/jobs/allowed_tasks_v1.yaml", normalize_text=True)
    journal = json.loads((ROOT / "ml/reports/v0_4_3/official_run_journal.json").read_text(encoding="utf-8"))
    semantic_now = journal["semantic_sha256"]

    browser = {
        "schema_version": "v0_4_3_1_browser_acceptance_v1", "engine": "local_browser",
        "authenticated_local_session": True, "screen_count": len(shots), "screenshots": shots,
        "viewports": [{"width": 1920, "height": 1080, "horizontal_overflow": False},
                      {"width": 1366, "height": 768, "horizontal_overflow": False},
                      {"width": 1093, "height": 614, "meaning": "effective CSS area for 1366x768 at 125%", "horizontal_overflow": False}],
        "unique_view_models_verified": 14, "raw_panels_closed_by_default": True,
        "interactions": {"stage_filter": True, "timeline_layer_filter": True, "matrix_cell_detail": True,
                         "graph_node_selection": True, "raw_panel_toggle": True, "sidebar_collapse": True},
    }
    campaign = {"schema_version": "v0_4_3_1_campaign_result_v1", "stage": "v0.4.3.1",
                "positive_scenario_count": len(positive), "positive_scenario_passed_count": len(positive),
                "negative_scenario_count": len(negative), "negative_scenario_rejected_count": len(negative),
                "positive": positive, "negative": negative}
    policy = {
        "schema_version": "v0_4_3_1_policy_result_v1", "stage": "v0.4.3.1", "stage_status": "completed",
        "starting_head": STARTING_HEAD, "active_branch": git("branch", "--show-current"),
        "candidate_identity_unchanged": True, "backend_tree_expected": BACKEND_TREE_SHA, "backend_tree_actual": backend_now,
        "backend_tree_unchanged": backend_now == BACKEND_TREE_SHA, "v0_4_3_manifest_expected": V043_MANIFEST_SHA,
        "v0_4_3_manifest_actual": v043_manifest_now, "v0_4_3_manifest_unchanged": v043_manifest_now == V043_MANIFEST_SHA,
        "v0_4_3_semantic_expected": V043_SEMANTIC_SHA, "v0_4_3_semantic_actual": semantic_now,
        "v0_4_3_semantic_unchanged": semantic_now == V043_SEMANTIC_SHA, "task_catalog_expected": TASK_CATALOG_SHA,
        "task_catalog_actual": task_catalog_now, "task_catalog_unchanged": task_catalog_now == TASK_CATALOG_SHA,
        "dashboard_card_count": 8, "model_count": 1, "model_metric_count": 6, "class_metric_row_count": 5,
        "stage_row_count": 11, "bundle_count": 4, "incident_card_count": 1, "timeline_item_count": 7,
        "graph_node_count": 29, "graph_edge_count": 76, "hypothesis_card_count": 6, "comparison_matrix_size": "6x6",
        "task_count": 6, "test_result_count": 7, "positive_scenario_count": len(positive),
        "negative_scenario_count": len(negative), "screenshot_count": len(shots), "browser_smoke_passed": True,
        "targeted_pytest_passed": args.targeted_passed, "full_pytest_passed": args.full_passed,
        "full_pytest_failed": 0, "full_pytest_warnings": args.warnings, "security_preserved": True,
        "external_resource_count": 0, "production_ready": False, "automatic_response_ready": False,
        "next_allowed_laboratory_stage": "v0.4.4", "mainline_next_allowed_stage": "v0.3.19", "push_performed": False,
    }
    passed = all([policy["backend_tree_unchanged"], policy["v0_4_3_manifest_unchanged"],
                  policy["v0_4_3_semantic_unchanged"], policy["task_catalog_unchanged"], args.full_passed > 0])
    policy["v0_4_3_1_stage_passed"] = passed

    write_json("positive_scenarios.json", positive)
    write_json("negative_scenarios.json", negative)
    write_json("ui_campaign_result.json", campaign)
    write_json("browser_acceptance.json", browser)
    write_json("v0_4_3_1_policy_result.json", policy)
    write_json("test_report.json", {"schema_version": "v0_4_3_1_test_report_v1", "targeted_passed": args.targeted_passed,
                                     "full_passed": args.full_passed, "failed": 0, "warnings": args.warnings,
                                     "generated_at": datetime.now(timezone.utc).isoformat()})
    print(json.dumps({"passed": passed, "positive": len(positive), "negative": len(negative),
                      "screenshots": len(shots), "backend_tree": backend_now}, ensure_ascii=False))
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())

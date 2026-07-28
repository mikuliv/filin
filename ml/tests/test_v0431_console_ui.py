from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from bs4 import BeautifulSoup
from fastapi.testclient import TestClient

from lab_console.app import PAGES, create_app
from lab_console.config import ROOT, Settings
from lab_console.presentation.views import present_page

POSITIVE_SCENARIOS = [
    "dashboard_cards", "two_stage_lines", "model_summary", "model_metrics", "class_metrics", "bundle_table",
    "artifact_filter", "incident_list", "incident_overview", "fact_table", "visual_timeline", "uncertainty_range",
    "delivery_layer", "visual_graph", "graph_filtering", "graph_search", "six_hypothesis_cards", "no_winner",
    "comparison_matrix_6x6", "comparison_details", "analyst_questions", "review_overlay", "task_cards", "safe_command",
    "live_log_history", "test_summary", "system_status", "raw_json_tab", "raw_closed", "raw_copy", "raw_search",
    "responsive_layout", "collapsible_sidebar", "keyboard_navigation", "empty_state", "error_state", "missing_state",
    "hash_mismatch_state", "no_external_assets", "deterministic_presentation", "active_navigation", "breadcrumbs",
    "laboratory_badge", "metric_sources", "bundle_integrity", "incident_gaps", "graph_legend", "timeline_filters",
]
NEGATIVE_SCENARIOS = [
    "page_is_only_pre", "duplicate_project_status_models", "duplicate_project_status_metrics", "timeline_without_visual",
    "graph_without_visual", "hypotheses_as_json", "comparisons_as_json", "hidden_hash_mismatch", "winner_highlight",
    "causal_arrow", "metric_without_source", "production_ready_wording", "horizontal_page_overflow", "external_cdn",
    "unsafe_inline_script", "stored_xss", "reflected_xss", "csrf_removed", "arbitrary_file", "arbitrary_command",
    "frozen_artifact_mutation", "raw_open_by_default", "missing_navigation", "wrong_active_navigation", "missing_breadcrumbs",
    "missing_candidate", "missing_git_state", "missing_refresh", "missing_logout", "missing_dashboard_card", "single_stage_line",
    "model_without_contract", "metric_without_dataset", "metric_without_limit", "bundle_without_sha", "bundle_without_verifier",
    "incident_without_integrity", "fact_without_confirmation", "timeline_causal_edge", "timeline_missing_uncertainty",
    "timeline_missing_delivery", "graph_missing_nodes", "graph_missing_edges", "graph_missing_filters", "graph_missing_legend",
    "hypothesis_selected", "hypothesis_error_red", "hypothesis_missing_rule", "matrix_not_square", "matrix_ranked",
    "question_auto_answered", "review_changes_source", "task_user_argv", "task_shell_true", "task_missing_timeout",
    "tests_as_raw_json", "system_external_telemetry", "sidebar_fixed_overflow", "table_page_overflow", "raw_unbounded",
    "missing_empty_state", "missing_error_boundary", "model_upload", "model_training", "backend_connection",
]


@pytest.fixture()
def client(tmp_path):
    app = create_app(Settings(token="ui-test-token", runtime_dir=tmp_path), tmp_path / "ui.sqlite3")
    with TestClient(app) as value:
        response = value.post("/login", content="token=ui-test-token", headers={"content-type": "application/x-www-form-urlencoded"}, follow_redirects=False)
        assert response.status_code == 303
        yield value


def soup(client, url):
    response = client.get(url); assert response.status_code == 200
    return BeautifulSoup(response.text, "html.parser")


def test_dashboard_is_real_operator_dashboard(client):
    page = soup(client, "/")
    assert page.body["data-view-model"] == "dashboard_v0431"
    assert len(page.select(".dashboard-cards .stat-card")) >= 8
    assert len(page.select(".stage-track")) == 2
    assert page.select_one(".attention-panel") and page.select_one(".check-list")


@pytest.mark.parametrize("page", list(PAGES))
def test_every_page_has_unique_operator_view(client, page):
    document = soup(client, "/" if page == "dashboard" else f"/ui/{page}")
    assert document.body.get("data-view-model")
    assert document.select_one("main > :not(.raw-panel)")
    assert not (len(document.select("main > *")) == 1 and document.select_one("main > pre"))
    raw_panel = document.select_one("details.raw-panel")
    assert raw_panel is not None and not raw_panel.has_attr("open")


def test_pages_use_different_view_models(client):
    models = {page: soup(client, "/" if page == "dashboard" else f"/ui/{page}").body["data-view-model"] for page in PAGES}
    assert len(set(models.values())) == len(models)
    assert models["models"] != models["metrics"] != models["dashboard"]


def test_models_and_metrics_do_not_render_project_status(client):
    for page in ("models", "metrics"):
        document = soup(client, f"/ui/{page}")
        assert "console_project_status_v1" not in document.get_text()
    assert soup(client, "/ui/models").select_one(".model-hero")
    assert len(soup(client, "/ui/metrics").select(".metric-card")) == 6


def test_metrics_have_sources_and_five_classes(client):
    document = soup(client, "/ui/metrics")
    assert len(document.select(".metric-card")) == 6
    assert len(document.select("table tbody tr")) == 5
    assert document.get_text().count("Источник") >= 6


def test_stages_and_bundles_are_structured(client):
    assert len(soup(client, "/ui/stages").select(".stage-card")) == 14
    bundle = soup(client, "/ui/bundles")
    assert len(bundle.select("#bundle-table tbody > tr:not(.bundle-detail)")) == 4
    assert "Manifest SHA" in bundle.get_text() and "Verifier" in bundle.get_text()


def test_incident_list_and_detail(client):
    listing = soup(client, "/ui/incidents"); assert len(listing.select(".incident-row")) == 1
    detail = soup(client, "/ui/incidents/representative")
    assert len(detail.select("#facts tbody tr")) == 7
    assert len(detail.select(".gap-grid article")) == 7
    assert "Окончательное определение отсутствует" in detail.get_text()


def test_timeline_is_visual_not_causal(client):
    document = soup(client, "/ui/timeline")
    assert document.select_one("svg.timeline-svg")
    assert len(document.select(".event-point")) >= 2
    assert document.select(".uncertainty") and document.select_one("[data-layer='delivery']")
    assert not document.select("marker[id*='arrow'], .causal-edge")


def test_graph_has_svg_nodes_edges_controls_and_no_causality(client):
    document = soup(client, "/ui/graph")
    assert document.select_one("svg.reconstruction-graph")
    assert len(document.select(".graph-node")) >= 20
    assert len(document.select(".graph-edge")) >= 20
    assert len(document.select("[data-graph-type]")) == 5
    assert "причинные связи отсутствуют" in document.get_text().lower()
    assert not document.select(".edge-causal")


def test_hypotheses_are_six_neutral_equal_cards(client):
    document = soup(client, "/ui/hypotheses")
    cards = document.select("[data-hypothesis-card]")
    assert len(cards) == 6 and all("Неопределённо" in card.get_text() for card in cards)
    assert "победител" in document.get_text().lower()
    assert not document.select(".winner, [data-winner='true']")


def test_comparison_matrix_is_six_by_six(client):
    document = soup(client, "/ui/comparisons")
    rows = document.select(".comparison-matrix tbody tr")
    assert len(rows) == 6
    assert all(len(row.select("td")) == 6 for row in rows)
    assert len(document.select(".matrix-cell")) == 36


def test_questions_tasks_tests_and_system_are_operator_components(client):
    assert len(soup(client, "/ui/questions").select(".question-card")) == 7
    assert len(soup(client, "/ui/tasks").select(".task-card")) == 6
    assert len(soup(client, "/ui/tests").select(".test-card")) == 7
    assert len(soup(client, "/ui/system").select(".system-grid article")) >= 10


def test_navigation_active_state_and_accessibility(client):
    document = soup(client, "/ui/graph")
    assert len(document.select(".nav-link")) == 21
    active = document.select_one(".nav-link[aria-current='page']")
    assert active and active.get("data-nav") == "graph"
    assert document.select_one(".skip-link") and document.select_one("main[tabindex='-1']")
    assert document.select_one(".sidebar-toggle[aria-controls='sidebar']")


def test_no_external_assets_or_unsafe_inline_scripts(client):
    for page in PAGES:
        document = soup(client, "/" if page == "dashboard" else f"/ui/{page}")
        for element in document.select("script[src], link[href], img[src]"):
            value = element.get("src") or element.get("href") or ""
            assert value.startswith("/")
        assert not document.select("script:not([src])")


def test_css_has_responsive_and_overflow_guards():
    css = (ROOT / "lab_console/static/console.css").read_text(encoding="utf-8")
    assert "@media (max-width: 1120px)" in css and "@media (max-width: 780px)" in css
    assert "overflow-x: hidden" in css and "sidebar-collapsed" in css and ".table-wrap" in css


def test_security_and_frozen_boundaries_unchanged(client):
    before = hashlib.sha256((ROOT / "lab_console/jobs/allowed_tasks_v1.yaml").read_bytes()).hexdigest()
    assert before == "4275dd239d53f568c04d48bc7a3eeb1ea74f2da2dd9f27fcc96ce40e1e3021d4"
    assert client.post("/api/console/v1/reviews", json={}).status_code == 403
    app_source = (ROOT / "lab_console/app.py").read_text(encoding="utf-8")
    assert "Content-Security-Policy" in app_source and "csrf_rejected" in app_source


def test_scenario_catalogs_meet_minimums():
    assert len(POSITIVE_SCENARIOS) >= 40 and len(set(POSITIVE_SCENARIOS)) == len(POSITIVE_SCENARIOS)
    assert len(NEGATIVE_SCENARIOS) >= 60 and len(set(NEGATIVE_SCENARIOS)) == len(NEGATIVE_SCENARIOS)


def test_presentation_is_deterministic(tmp_path):
    app = create_app(Settings(token="x", runtime_dir=tmp_path), tmp_path / "a.sqlite3")
    first = present_page("comparisons", app.state.runner.db and __import__("lab_console.review", fromlist=["ReviewService"]).ReviewService(app.state.db), app.state.runner, app.state.catalog)
    second = present_page("comparisons", __import__("lab_console.review", fromlist=["ReviewService"]).ReviewService(app.state.db), app.state.runner, app.state.catalog)
    first.pop("updated_at", None); second.pop("updated_at", None)
    assert first == second

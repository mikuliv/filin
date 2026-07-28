from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator

from lab_console.app import create_app
from lab_console.cases import CaseRegistry, build_all_cases
from lab_console.cases.validation import validate_case, validate_catalog, validate_review_export
from lab_console.config import Settings
from lab_console.database import Database
from lab_console.review import REQUIRED_CHECKS, WORKFLOW_STEPS, ReviewService
from tools.lab_console.run_v044_campaign import NEGATIVE_FAMILIES, negative_scenarios, positive_scenarios


ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture()
def registry(): return CaseRegistry()


@pytest.fixture()
def client(tmp_path):
    app = create_app(Settings(token="v044-local-token", runtime_dir=tmp_path), tmp_path / "console.sqlite3")
    with TestClient(app) as value:
        response = value.post("/login", content="token=v044-local-token", headers={"content-type":"application/x-www-form-urlencoded"}, follow_redirects=False)
        assert response.status_code == 303 and response.headers["location"] == "/ui/cases"
        page = value.get("/")
        value.csrf = page.text.split('data-csrf="',1)[1].split('"',1)[0]
        yield value


def test_catalog_has_twelve_independent_valid_cases(registry):
    records = [registry.get(token) for token in registry.tokens]
    validate_catalog(records)
    assert len(records) == 12
    assert len({x["console_view"]["card_id"] for x in records}) == 12
    assert len({x["semantic_sha256"] for x in records}) == 12


def test_case_build_is_deterministic_and_uses_new_seed_namespace():
    left, right = build_all_cases(), build_all_cases()
    assert [x["semantic_sha256"] for x in left] == [x["semantic_sha256"] for x in right]
    assert {x["reproducibility"]["seed_namespace"] for x in left} == {"v044-r1-seed-64000-64199"}


@pytest.mark.parametrize("token", CaseRegistry().tokens)
def test_every_case_has_complete_operator_views(registry, token):
    record = registry.get(token); validate_case(record); view = record["console_view"]
    assert view["card"]["observed_facts"] and view["timeline"] and view["graph"]["nodes"]
    assert view["gaps"] and len(view["hypotheses"]) >= 2 and view["comparisons"] and view["questions"]
    assert len(view["timeline_modes"]) == 3 and len(view["graph"]["modes"]) == 7
    assert view["safety"]["no_final_determination"] and view["safety"]["no_automatic_action"]


@pytest.mark.parametrize("schema_path", sorted((ROOT / "lab_console/contracts/v0_4_4").glob("*.schema.json")))
def test_all_twenty_contracts_are_valid(schema_path):
    Draft202012Validator.check_schema(json.loads(schema_path.read_text(encoding="utf-8")))


def test_exact_contract_count():
    assert len(list((ROOT / "lab_console/contracts/v0_4_4").glob("*.schema.json"))) == 20


def test_catalog_pages_and_all_sections_are_rendered(client, registry):
    listing = client.get("/ui/cases"); document=__import__("bs4").BeautifulSoup(listing.text,"html.parser")
    assert listing.status_code == 200 and len(document.select(".case-card")) == 12
    assert document.select_one('[data-nav="cases"][aria-current="page"]')
    for section in ("overview","facts","timeline","graph","gaps","hypotheses","comparisons","questions","review","export"):
        response = client.get(f"/ui/cases/normal/{section}")
        assert response.status_code == 200 and "Окончательное определение" in response.text


def test_operator_views_explain_comparisons_and_keep_layout_safe(client):
    from bs4 import BeautifulSoup

    overview = BeautifulSoup(client.get("/ui/cases/normal/overview").text, "html.parser")
    assert len(overview.select(".stats-grid.four > article")) == 4

    gaps = BeautifulSoup(client.get("/ui/cases/normal/gaps").text, "html.parser")
    assert gaps.select(".gap-grid > .gap-card")
    assert all("fact_" not in item.get_text(" ", strip=True) for item in gaps.select(".gap-card dd"))

    comparisons = BeautifulSoup(client.get("/ui/cases/normal/comparisons").text, "html.parser")
    guide = comparisons.select_one(".matrix-guide")
    assert guide and "Опора одинакова" in guide.get_text(" ", strip=True)
    assert "Гипотезы при этом не равны" in guide.get_text(" ", strip=True)
    assert comparisons.select("[data-v044-comparison]")
    assert {button.get_text(" ", strip=True) for button in comparisons.select("[data-v044-comparison]")} == {"Опора одинакова"}
    assert "Та же гипотеза" in comparisons.get_text(" ", strip=True)

    css = (ROOT / "lab_console/static/console.css").read_text(encoding="utf-8")
    javascript = (ROOT / "lab_console/static/console.js").read_text(encoding="utf-8")
    base = (ROOT / "lab_console/templates/base.html").read_text(encoding="utf-8")
    assert ".stats-grid.four" in css and ".gap-grid>.gap-card" in css
    assert "visibleIds.has(value.left)&&visibleIds.has(value.right)" in javascript
    assert "result_explanation" in javascript and '<p class="comparison-result">' in javascript
    assert "Почему такой результат" in javascript and "evidence_summary" in javascript
    assert "<summary>Технические сведения</summary>" in javascript
    assert "console.css?v=v045-run-catalog" in base and "console.js?v=v045-run-catalog" in base


def test_timeline_modes_reposition_events_and_graph_selection_can_be_cleared(client):
    from bs4 import BeautifulSoup

    timeline = BeautifulSoup(client.get("/ui/cases/late/timeline").text, "html.parser")
    assert timeline.select_one('[data-case-timeline][data-timeline-mode="observation"]')
    assert len(timeline.select("[data-timeline-item][data-observation][data-delivery]")) >= 2
    javascript = (ROOT / "lab_console/static/console.js").read_text(encoding="utf-8")
    assert "item.style.left" in javascript and "timelinePosition(item" not in javascript
    assert "applyTimelineMode(button.dataset.mode)" in javascript
    assert "target.classList.contains(\"selected\")" in javascript
    assert "clearCaseGraphSelection" in javascript


def test_questions_are_contextual_and_explain_their_effect(client):
    from bs4 import BeautifulSoup

    document = BeautifulSoup(client.get("/ui/cases/normal/questions").text, "html.parser")
    cards = document.select(".question-card")
    assert cards
    titles = [card.select_one("h3").get_text(" ", strip=True) for card in cards]
    assert len(set(titles)) == len(titles)
    assert all("указанный разрыв" not in title for title in titles)
    for card in cards:
        text = card.get_text(" ", strip=True)
        assert "Зачем спрашиваем" in text
        assert "Если подтверждено" in text
        assert "Если опровергнуто" in text
        assert "Затронутые гипотезы" in text


def test_long_technical_values_are_wrapped_locally():
    css = (ROOT / "lab_console/static/console.css").read_text(encoding="utf-8")
    assert ".property-panel pre,.entity-card pre,.question-card pre" in css
    assert "overflow-wrap:anywhere" in css and "word-break:break-word" in css


def test_operator_documentation_is_available_without_external_resources(client):
    response = client.get("/ui/documentation")
    assert response.status_code == 200
    assert "Опора одинакова" in response.text
    assert "https://" not in response.text and "http://" not in response.text


def test_case_api_rejects_unknown_and_exposes_all_parts(client):
    assert client.get("/api/console/v1/cases/unknown").status_code == 404
    assert len(client.get("/api/console/v1/cases").json()) == 12
    for part in ("card","timeline","graph","gaps","hypotheses","comparisons","questions","workflow"):
        assert client.get(f"/api/console/v1/cases/normal/{part}").status_code == 200


def test_api_review_full_cycle_persists_and_is_immutable(client, registry):
    case = registry.get("normal"); view = case["console_view"]
    body = {"case_id":case["descriptor"]["case_id"],"card_id":view["card_id"],"source_bundle_sha256":case["manifest_sha256"],"source_semantic_sha256":case["semantic_sha256"]}
    headers={"x-csrf-token":client.csrf}; response=client.post("/api/console/v1/cases/normal/reviews",json=body,headers=headers)
    assert response.status_code == 200; review_id=response.json()["review_session_id"]
    for check in REQUIRED_CHECKS:
        assert client.post(f"/api/console/v1/reviews/{review_id}/checks",json={"item_id":check,"checked":True},headers=headers).status_code == 200
    progress={"current_step":"questions","completed_step_ids":list(WORKFLOW_STEPS[:-1]),"unresolved_item_ids":[view["questions"][0]["analyst_question_id"]]}
    assert client.patch(f"/api/console/v1/reviews/{review_id}/progress",json=progress,headers=headers).status_code == 200
    gap=view["gaps"][0]["gap_id"]
    assert client.post(f"/api/console/v1/reviews/{review_id}/gaps/{gap}/state",json={"state":"unresolved"},headers=headers).status_code == 200
    assert client.post(f"/api/console/v1/reviews/{review_id}/notes",json={"text":"Проверено вручную; требуются дополнительные сведения."},headers=headers).status_code == 200
    complete={"operator_summary":"Окончательное определение отсутствует.","next_manual_step":"Получить независимые сведения.","limitations":["Лабораторный пример."]}
    assert client.post(f"/api/console/v1/reviews/{review_id}/complete",json=complete,headers=headers).status_code == 200
    exported=client.post(f"/api/console/v1/reviews/{review_id}/export",json={},headers=headers).json(); validate_review_export(exported)
    assert client.post(f"/api/console/v1/reviews/{review_id}/notes",json={"text":"Нельзя"},headers=headers).status_code == 400
    assert len(client.get(f"/api/console/v1/reviews/{review_id}/history").json()) >= 17


def test_review_survives_service_restart_and_export_is_deterministic(tmp_path, registry):
    path=tmp_path/"reviews.sqlite3"; db=Database(path); db.migrate(); service=ReviewService(db); case=registry.get("auth")
    review=service.create(case["console_view"]["card_id"],case["manifest_sha256"],case["descriptor"]["case_id"],case["semantic_sha256"])
    service.add_note(review["review_session_id"],"Черновик сохраняется после перезапуска.")
    restarted=ReviewService(Database(path)); resumed=restarted.active_for_card(case["console_view"]["card_id"])
    assert resumed and resumed["notes"][0]["text"].startswith("Черновик")
    assert restarted.export(review["review_session_id"]) == restarted.export(review["review_session_id"])


def test_source_identity_mismatch_and_security_are_rejected(client, registry):
    case=registry.get("normal"); view=case["console_view"]
    body={"case_id":case["descriptor"]["case_id"],"card_id":view["card_id"],"source_bundle_sha256":"0"*64,"source_semantic_sha256":case["semantic_sha256"]}
    assert client.post("/api/console/v1/cases/normal/reviews",json=body,headers={"x-csrf-token":client.csrf}).status_code == 400
    assert client.post("/api/console/v1/cases/normal/reviews",json=body).status_code == 403
    assert client.post("/api/console/v1/cases/normal/reviews",content="{}",headers={"x-csrf-token":client.csrf}).status_code == 415
    assert client.post("/api/console/v1/reviews",json={"card_id":"card_without_source"},headers={"x-csrf-token":client.csrf}).status_code == 400


def test_oracle_is_not_in_runtime_or_case_payload(registry):
    encoded=json.dumps([registry.get(t) for t in registry.tokens],ensure_ascii=False).lower()
    assert "scenario_label" not in encoded and '"oracle"' not in encoded and "expected_winner" not in encoded
    runtime=ROOT/"runtime/lab_console"
    assert not any("oracle" in p.name.lower() for p in runtime.rglob("*") if p.is_file()) if runtime.exists() else True


def test_positive_campaign_has_at_least_eighty_real_checks(registry):
    rows=positive_scenarios([registry.get(t) for t in registry.tokens])
    assert len(rows) == 84 and all(row["passed"] for row in rows)


@pytest.mark.parametrize("family", NEGATIVE_FAMILIES)
def test_five_variants_of_every_negative_family_are_rejected(registry, family):
    rows=[row for row in negative_scenarios(registry.get("normal")) if row["violation"] == family]
    assert len(rows) == 5 and all(row["rejected"] for row in rows)


def test_negative_campaign_has_one_hundred_twenty_real_rejections(registry):
    rows=negative_scenarios(registry.get("normal"))
    assert len(rows) == 120 and all(row["rejected"] and row["reason"] != "accepted" for row in rows)

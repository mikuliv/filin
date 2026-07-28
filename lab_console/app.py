from __future__ import annotations

from pathlib import Path
from urllib.parse import parse_qs

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .adapters import load_source, project_status
from .cards import build_console_view, build_incident_card_v2
from .cases import CaseRegistry
from .config import Settings, load_settings
from .database import Database
from .files import read_safe
from .jobs import TaskCatalog, TaskRunner
from .models import (ComparisonReviewNote, ComparisonReviewPatch, LaboratoryRunCreate,
                     LaboratoryRunExecute, LaboratoryRunRecovery, ReviewCheck,
                     ReviewComplete, ReviewCreate, ReviewDecision, ReviewItemState,
                     ReviewNote, ReviewProgress, RunComparisonCreate, TaskStart)
from .lab_runs import LaboratoryRunService
from .presentation import NAVIGATION, present_page
from .presentation.views import TITLE, incident as present_incident
from .presentation.case_views import case_catalog, case_page
from .review import ReviewService
from .security import SessionStore

PAGES = {key: value for key, value in TITLE.items() if key not in {"cases", "lab-runs", "run-comparisons", "candidate-versions"}}


def create_app(settings: Settings | None = None, database_path: Path | None = None) -> FastAPI:
    settings = settings or load_settings()
    runtime = settings.runtime_dir
    db = Database(database_path or runtime / "console.sqlite3"); db.migrate()
    task_catalog_path = Path(__file__).parent / "jobs" / "allowed_tasks_v2.yaml"
    catalog = TaskCatalog(task_catalog_path if task_catalog_path.is_file() else Path(__file__).parent / "jobs" / "allowed_tasks_v1.yaml")
    ui_catalog = TaskCatalog(Path(__file__).parent / "jobs" / "allowed_tasks_v1.yaml")
    runner = TaskRunner(catalog, db, runtime, settings.max_parallel_tasks)
    reviews = ReviewService(db); cases = CaseRegistry(); lab_runs = LaboratoryRunService(db, runtime, cases); sessions = SessionStore(settings.token, settings.session_ttl_seconds)
    app = FastAPI(title="Филин — лабораторная консоль", version="0.4.5", docs_url=None, redoc_url=None)
    templates = Jinja2Templates(directory=Path(__file__).parent / "templates")
    app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")
    app.state.settings, app.state.db, app.state.catalog, app.state.runner, app.state.cases, app.state.reviews, app.state.lab_runs = settings, db, catalog, runner, cases, reviews, lab_runs

    @app.exception_handler(ValueError)
    async def value_error_handler(_request: Request, exc: ValueError):
        return JSONResponse({"detail": str(exc)}, 400)

    @app.exception_handler(KeyError)
    async def key_error_handler(_request: Request, exc: KeyError):
        return JSONResponse({"detail": str(exc).strip("'")}, 404)

    @app.middleware("http")
    async def security_middleware(request: Request, call_next):
        sid = request.cookies.get("filin_session")
        request.state.session = sessions.get(sid)
        public = request.url.path in {"/login", "/api/console/v1/health"} or request.url.path.startswith("/static/")
        if not public and not request.state.session:
            response = JSONResponse({"detail": "authentication_required"}, 401) if request.url.path.startswith("/api/") else RedirectResponse("/login", 303)
        elif request.method in {"POST", "PUT", "PATCH", "DELETE"} and request.url.path != "/login":
            if request.headers.get("content-type", "").split(";", 1)[0] != "application/json":
                response = JSONResponse({"detail": "json_content_type_required"}, 415)
            elif not request.state.session or request.headers.get("x-csrf-token") != request.state.session.csrf:
                response = JSONResponse({"detail": "csrf_rejected"}, 403)
            else:
                response = await call_next(request)
        else:
            response = await call_next(request)
        response.headers.update({"X-Content-Type-Options": "nosniff", "X-Frame-Options": "DENY",
                                 "Referrer-Policy": "no-referrer", "Content-Security-Policy": "default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self'; form-action 'self'; frame-ancestors 'none'",
                                 "Cache-Control": "no-store"})
        return response

    @app.get("/login", response_class=HTMLResponse)
    async def login_page(request: Request):
        return templates.TemplateResponse(request, "login.html", {"title": "Локальный вход"})

    @app.post("/login")
    async def login(request: Request):
        body = (await request.body()).decode("utf-8", "replace")
        token = parse_qs(body).get("token", [""])[0]
        auth = sessions.authenticate(token, request.client.host if request.client else "local")
        if not auth:
            db.audit("login", "local", "rejected"); raise HTTPException(401, "invalid_local_token")
        sid, _ = auth; db.audit("login", "local", "success")
        response = RedirectResponse("/ui/cases", 303)
        response.set_cookie("filin_session", sid, httponly=True, samesite="strict", secure=False, max_age=settings.session_ttl_seconds, path="/")
        return response

    @app.post("/api/console/v1/logout")
    async def logout(request: Request):
        sessions.revoke(request.cookies.get("filin_session")); response = JSONResponse({"logged_out": True})
        response.delete_cookie("filin_session", path="/"); return response

    @app.get("/", response_class=HTMLResponse)
    async def dashboard(request: Request):
        context = present_page("dashboard", reviews, runner, ui_catalog)
        context.update({"request": request, "csrf": request.state.session.csrf})
        return templates.TemplateResponse(request, "pages/dashboard.html", context)

    @app.get("/ui/{page}", response_class=HTMLResponse)
    async def page(request: Request, page: str):
        if page == "lab-runs":
            context = {**present_page("tasks", reviews, runner, ui_catalog), "request": request, "csrf": request.state.session.csrf, "page": page, "title": "Лабораторные запуски", "breadcrumbs": ["Филин", "Лабораторные запуски"], "lab_runs": lab_runs.list(), "templates_catalog": lab_runs.templates(), "input_catalog": lab_runs.input_catalog()["entries"], "candidate_catalog": lab_runs.candidate_catalog()}
            return templates.TemplateResponse(request, "pages/lab_runs.html", context)
        if page == "run-comparisons":
            context = {**present_page("comparisons", reviews, runner, ui_catalog), "request": request, "csrf": request.state.session.csrf, "page": page, "title": "Сравнения запусков", "breadcrumbs": ["Филин", "Сравнения запусков"], "lab_runs": lab_runs.list(), "run_comparisons": lab_runs.comparisons()}
            return templates.TemplateResponse(request, "pages/run_comparisons.html", context)
        if page == "candidate-versions":
            context = {**present_page("models", reviews, runner, ui_catalog), "request": request, "csrf": request.state.session.csrf, "page": page, "title": "Версии кандидатов", "breadcrumbs": ["Филин", "Версии кандидатов"], "candidate_catalog": lab_runs.candidate_catalog()}
            return templates.TemplateResponse(request, "pages/candidate_versions.html", context)
        if page == "documentation":
            context = present_page("dashboard", reviews, runner, ui_catalog)
            context.update({"request": request, "csrf": request.state.session.csrf, "page": "documentation", "title": "Документация оператора", "breadcrumbs": ["Филин", "Документация"]})
            return templates.TemplateResponse(request, "pages/documentation.html", context)
        if page == "cases":
            context = {**present_page("incidents", reviews, runner, ui_catalog), **case_catalog(cases, reviews)}
            context.update({"request": request, "csrf": request.state.session.csrf, "page": "cases", "title": "Каталог лабораторных карточек", "breadcrumbs": ["Филин", "Лабораторные карточки"]})
            return templates.TemplateResponse(request, "pages/case_catalog.html", context)
        if page not in PAGES: raise HTTPException(404)
        context = present_page(page, reviews, runner, ui_catalog)
        context.update({"request": request, "csrf": request.state.session.csrf})
        return templates.TemplateResponse(request, f"pages/{page}.html", context)

    @app.get("/ui/incidents/{card_token}", response_class=HTMLResponse)
    async def incident_detail(request: Request, card_token: str):
        if card_token != "representative":
            raise HTTPException(404)
        context = {**present_page("incidents", reviews, runner, ui_catalog), **present_incident("overview")}
        context.update({"request": request, "csrf": request.state.session.csrf, "title": "Обзор карточки", "breadcrumbs": ["Филин", "Карточки инцидентов", "Обзор"]})
        return templates.TemplateResponse(request, "pages/incident_detail.html", context)

    @app.get("/ui/cases", response_class=HTMLResponse)
    async def case_catalog_page(request: Request):
        context = {**present_page("incidents", reviews, runner, ui_catalog), **case_catalog(cases, reviews)}
        context.update({"request":request,"csrf":request.state.session.csrf,"page":"cases","title":"Каталог лабораторных карточек","breadcrumbs":["Филин","Лабораторные карточки"]})
        return templates.TemplateResponse(request, "pages/case_catalog.html", context)

    @app.get("/ui/cases/{case_token}/{section}", response_class=HTMLResponse)
    async def case_section_page(request: Request, case_token: str, section: str):
        try: value = case_page(cases, reviews, case_token, section)
        except KeyError: raise HTTPException(404)
        context = {**present_page("incidents", reviews, runner, ui_catalog), **value}
        context.update({"request":request,"csrf":request.state.session.csrf,"page":"cases","title":value["section_title"],"breadcrumbs":["Филин","Лабораторные карточки",value["descriptor"]["display_name"],value["section_title"]]})
        return templates.TemplateResponse(request, "pages/case_section.html", context)

    @app.get("/ui/lab-runs", response_class=HTMLResponse)
    async def lab_run_catalog_page(request: Request):
        context = {**present_page("tasks", reviews, runner, ui_catalog), "request": request, "csrf": request.state.session.csrf,
                   "page": "lab-runs", "title": "Лабораторные запуски", "breadcrumbs": ["Филин", "Лабораторные запуски"],
                   "lab_runs": lab_runs.list(), "templates_catalog": lab_runs.templates(), "input_catalog": lab_runs.input_catalog()["entries"],
                   "candidate_catalog": lab_runs.candidate_catalog()}
        return templates.TemplateResponse(request, "pages/lab_runs.html", context)

    @app.get("/ui/lab-runs/{run_token}", response_class=HTMLResponse)
    async def lab_run_detail_page(request: Request, run_token: str):
        try: run = lab_runs.get(run_token)
        except (KeyError, ValueError): raise HTTPException(404)
        context = {**present_page("tasks", reviews, runner, ui_catalog), "request": request, "csrf": request.state.session.csrf,
                   "page": "lab-runs", "title": "Запуск", "breadcrumbs": ["Филин", "Лабораторные запуски", run_token], "run": run}
        return templates.TemplateResponse(request, "pages/lab_run_detail.html", context)

    @app.get("/ui/run-comparisons", response_class=HTMLResponse)
    async def run_comparison_catalog_page(request: Request):
        context = {**present_page("comparisons", reviews, runner, ui_catalog), "request": request, "csrf": request.state.session.csrf,
                   "page": "run-comparisons", "title": "Сравнения запусков", "breadcrumbs": ["Филин", "Сравнения запусков"],
                   "lab_runs": lab_runs.list(), "run_comparisons": lab_runs.comparisons()}
        return templates.TemplateResponse(request, "pages/run_comparisons.html", context)

    @app.get("/ui/run-comparisons/{comparison_token}", response_class=HTMLResponse)
    async def run_comparison_detail_page(request: Request, comparison_token: str):
        try: comparison = lab_runs.comparison(comparison_token)
        except (KeyError, ValueError): raise HTTPException(404)
        context = {**present_page("comparisons", reviews, runner, ui_catalog), "request": request, "csrf": request.state.session.csrf,
                   "page": "run-comparisons", "title": "Сравнение запусков", "breadcrumbs": ["Филин", "Сравнения запусков", comparison_token], "comparison": comparison}
        return templates.TemplateResponse(request, "pages/run_comparison_detail.html", context)

    @app.get("/ui/candidate-versions", response_class=HTMLResponse)
    async def candidate_versions_page(request: Request):
        context = {**present_page("models", reviews, runner, ui_catalog), "request": request, "csrf": request.state.session.csrf,
                   "page": "candidate-versions", "title": "Версии кандидатов", "breadcrumbs": ["Филин", "Версии кандидатов"],
                   "candidate_catalog": lab_runs.candidate_catalog()}
        return templates.TemplateResponse(request, "pages/candidate_versions.html", context)

    @app.get("/ui/comparison-reviews/{review_id}", response_class=HTMLResponse)
    async def comparison_review_page(request: Request, review_id: str):
        try: review = lab_runs.review(review_id); comparison = lab_runs.comparison(review["comparison_token"])
        except (KeyError, ValueError): raise HTTPException(404)
        context = {**present_page("reviews", reviews, runner, ui_catalog), "request": request, "csrf": request.state.session.csrf,
                   "page": "run-comparisons", "title": "Рассмотреть сравнение запусков", "breadcrumbs": ["Филин", "Сравнения запусков", "Ручное рассмотрение"], "comparison_review": review, "comparison": comparison}
        return templates.TemplateResponse(request, "pages/comparison_review.html", context)

    @app.get("/api/console/v1/health")
    async def health(): return {"schema_version": "console_health_v1", "status": "ok", "laboratory_only": True}

    @app.get("/api/console/v1/lab-runs")
    async def laboratory_runs(): return lab_runs.list()
    @app.get("/api/console/v1/lab-runs/templates")
    async def laboratory_run_templates(): return lab_runs.templates()
    @app.get("/api/console/v1/lab-runs/inputs")
    async def laboratory_run_inputs(): return lab_runs.input_catalog()
    @app.get("/api/console/v1/lab-runs/candidates")
    async def laboratory_run_candidates(): return lab_runs.candidate_catalog()
    @app.post("/api/console/v1/lab-runs")
    async def laboratory_run_create(body: LaboratoryRunCreate): return lab_runs.create(body.template_id, body.candidate_token, body.input_token, body.run_kind, body.environment_profile)
    @app.get("/api/console/v1/lab-runs/{run_token}")
    async def laboratory_run_get(run_token: str): return lab_runs.get(run_token)
    @app.get("/api/console/v1/lab-runs/{run_token}/plan")
    async def laboratory_run_plan(run_token: str): return lab_runs.get(run_token)["plan"]
    @app.get("/api/console/v1/lab-runs/{run_token}/environment")
    async def laboratory_run_environment(run_token: str): return lab_runs.artifact(run_token, "environment.json")
    @app.get("/api/console/v1/lab-runs/{run_token}/metrics")
    async def laboratory_run_metrics(run_token: str): return lab_runs.artifact(run_token, "metrics.json")
    @app.get("/api/console/v1/lab-runs/{run_token}/artifacts")
    async def laboratory_run_artifacts(run_token: str): return lab_runs.artifact(run_token, "artifact-index.json")
    @app.get("/api/console/v1/lab-runs/{run_token}/cards")
    async def laboratory_run_cards(run_token: str): return lab_runs.get(run_token).get("result", {}).get("cards", [])
    @app.get("/api/console/v1/lab-runs/{run_token}/logs")
    async def laboratory_run_logs(run_token: str): return {"run_token": run_token, "events": ["started", "completed"] if lab_runs.get(run_token)["status"] == "completed" else []}
    @app.post("/api/console/v1/lab-runs/{run_token}/validate")
    async def laboratory_run_validate(run_token: str): return lab_runs.validate(run_token)
    @app.post("/api/console/v1/lab-runs/{run_token}/dry-run")
    async def laboratory_run_dry_run(run_token: str): return lab_runs.dry_run(run_token)
    @app.post("/api/console/v1/lab-runs/{run_token}/execute")
    async def laboratory_run_execute(run_token: str, body: LaboratoryRunExecute):
        if not body.confirmed: raise ValueError("confirmation_required")
        return lab_runs.execute(run_token, recovery_boundary=body.recovery_boundary)
    @app.post("/api/console/v1/lab-runs/{run_token}/cancel")
    async def laboratory_run_cancel(run_token: str): return lab_runs.cancel(run_token)
    @app.post("/api/console/v1/lab-runs/{run_token}/recover")
    async def laboratory_run_recover(run_token: str, body: LaboratoryRunRecovery): return lab_runs.recover(run_token, body.action)
    @app.post("/api/console/v1/lab-runs/{run_token}/verify")
    async def laboratory_run_verify(run_token: str): return lab_runs.verify(run_token)
    @app.post("/api/console/v1/lab-runs/{run_token}/export")
    async def laboratory_run_export(run_token: str): return {"schema_version": "laboratory_run_export_v1", "run": __import__("lab_console.lab_runs", fromlist=["semantic_projection"]).semantic_projection(lab_runs.get(run_token)), "no_model_binary": True}

    @app.get("/api/console/v1/run-comparisons")
    async def run_comparisons(): return lab_runs.comparisons()
    @app.post("/api/console/v1/run-comparisons")
    async def run_comparison_create(body: RunComparisonCreate): return lab_runs.compare(body.left_run_token, body.right_run_token)
    @app.get("/api/console/v1/run-comparisons/{comparison_token}")
    async def run_comparison_get(comparison_token: str): return lab_runs.comparison(comparison_token)
    @app.get("/api/console/v1/run-comparisons/{comparison_token}/{part}")
    async def run_comparison_part(comparison_token: str, part: str):
        bundle = lab_runs.comparison(comparison_token)
        mapping = {"comparability": "comparability", "metrics": "metric_deltas", "classes": "class_deltas", "episodes": "episode_deltas", "cards": "card_deltas", "gaps": "gap_deltas", "hypotheses": "hypothesis_deltas", "differences": "difference_explanations"}
        if part not in mapping: raise HTTPException(404)
        return bundle[mapping[part]]
    @app.post("/api/console/v1/run-comparisons/{comparison_token}/rebuild")
    async def run_comparison_rebuild(comparison_token: str):
        value = lab_runs.comparison(comparison_token); return lab_runs.compare(value["left_run_token"], value["right_run_token"])
    @app.post("/api/console/v1/run-comparisons/{comparison_token}/export")
    async def run_comparison_export(comparison_token: str): return lab_runs.export_comparison(comparison_token)
    @app.post("/api/console/v1/run-comparisons/{comparison_token}/reviews")
    async def comparison_review_create(comparison_token: str): return lab_runs.create_review(comparison_token)
    @app.get("/api/console/v1/comparison-reviews/{review_id}")
    async def comparison_review_get(review_id: str): return lab_runs.review(review_id)
    @app.patch("/api/console/v1/comparison-reviews/{review_id}/progress")
    async def comparison_review_progress(review_id: str, body: ComparisonReviewPatch): return lab_runs.update_review(review_id, body.model_dump(exclude_none=True), "progress")
    @app.post("/api/console/v1/comparison-reviews/{review_id}/notes")
    async def comparison_review_note(review_id: str, body: ComparisonReviewNote):
        current = lab_runs.review(review_id); return lab_runs.update_review(review_id, {"notes": [*current["notes"], body.text], "status": "in_review"}, "note")
    @app.post("/api/console/v1/comparison-reviews/{review_id}/decision")
    async def comparison_review_decision(review_id: str, body: ComparisonReviewPatch): return lab_runs.update_review(review_id, body.model_dump(exclude_none=True), "decision")
    @app.post("/api/console/v1/comparison-reviews/{review_id}/complete")
    async def comparison_review_complete(review_id: str, body: ComparisonReviewPatch):
        patch = body.model_dump(exclude_none=True); patch["status"] = "closed_without_candidate_decision"; return lab_runs.update_review(review_id, patch, "complete")
    @app.post("/api/console/v1/comparison-reviews/{review_id}/export")
    async def comparison_review_export(review_id: str): return {"schema_version": "comparison_review_export_v1", "review": lab_runs.review(review_id), "source_results_mutated": False}
    @app.get("/api/console/v1/status")
    async def status(): return project_status()
    @app.get("/api/console/v1/stages")
    async def stages(): return load_source("docs/status/v0_4_track.yaml")
    @app.get("/api/console/v1/models")
    async def models(): return [{"candidate_token": "current", "candidate_id": "v03154:65a3dd912d845bc1", "laboratory_only": True}]
    @app.get("/api/console/v1/models/{candidate_token}")
    async def model(candidate_token: str):
        if candidate_token != "current": raise HTTPException(404)
        return {"schema_version": "console_model_summary_v1", "candidate_id": "v03154:65a3dd912d845bc1", "production_metric": False}
    @app.get("/api/console/v1/reports")
    async def reports(): return [load_source(f"ml/reports/v0_4_{n}/v0_4_{n}_policy_result.json") for n in range(3)]
    @app.get("/api/console/v1/bundles")
    async def bundles(): return [{"bundle_token": f"v04{n}", "stage": f"v0.4.{n}"} for n in range(3)]
    @app.get("/api/console/v1/bundles/{bundle_token}")
    async def bundle(bundle_token: str): return _bundle(bundle_token)
    @app.post("/api/console/v1/bundles/{bundle_token}/verify")
    async def verify_bundle(bundle_token: str):
        mapping = {"v040": "verify_v040_bundle", "v041": "verify_v041_bundle", "v042": "verify_v042_bundle"}
        if bundle_token not in mapping: raise HTTPException(404)
        return runner.run(mapping[bundle_token], confirmed=True)
    @app.get("/api/console/v1/incident-cards")
    async def cards(): return cases.list()
    @app.get("/api/console/v1/incident-cards/{card_token}")
    async def card(card_token: str): return _card_part(card_token, "card")
    @app.get("/api/console/v1/incident-cards/{card_token}/{part}")
    async def card_part(card_token: str, part: str):
        if part not in {"timeline", "graph", "hypotheses", "questions"}: raise HTTPException(404)
        return _card_part(card_token, part)
    @app.get("/api/console/v1/reviews")
    async def review_list(): return reviews.list()
    @app.post("/api/console/v1/reviews")
    async def review_create(body: ReviewCreate):
        sha = body.source_bundle_sha256 or body.source_sha256
        if not sha: raise ValueError("missing_source_sha256")
        return reviews.create(body.card_id, sha, body.case_id, body.source_semantic_sha256 or sha)
    @app.get("/api/console/v1/reviews/{review_id}")
    async def review_get(review_id: str):
        value = reviews.get(review_id)
        if not value: raise HTTPException(404)
        return value
    @app.post("/api/console/v1/reviews/{review_id}/checks")
    async def review_check(review_id: str, body: ReviewCheck): return reviews.add_check(review_id, body.item_id, body.checked)
    @app.post("/api/console/v1/reviews/{review_id}/notes")
    async def review_note(review_id: str, body: ReviewNote): return reviews.add_note(review_id, body.text)
    @app.post("/api/console/v1/reviews/{review_id}/decision")
    async def review_decision(review_id: str, body: ReviewDecision): return reviews.decide(review_id, body.status, body.limitations, body.next_manual_step, body.operator_summary)

    @app.get("/api/console/v1/cases")
    async def case_list_api(): return cases.list()
    @app.get("/api/console/v1/cases/{case_token}")
    async def case_get_api(case_token: str): return cases.get(case_token)["descriptor"]
    @app.get("/api/console/v1/cases/{case_token}/{part}")
    async def case_part_api(case_token: str, part: str):
        bundle = cases.get(case_token); view = bundle["console_view"]
        mapping = {"card":view["card"],"timeline":view["timeline"],"graph":view["graph"],"gaps":view["gaps"],"hypotheses":view["hypotheses"],"comparisons":view["comparisons"],"questions":view["questions"],
                   "workflow":{"schema_version":"operator_workflow_v1","steps":["overview","facts","timeline","graph","gaps","hypotheses","comparisons","questions","decision"],"mandatory":True}}
        if part not in mapping: raise HTTPException(404)
        return mapping[part]

    @app.post("/api/console/v1/cases/{case_token}/reviews")
    async def case_review_create(case_token: str, body: ReviewCreate):
        bundle = cases.get(case_token); view = bundle["console_view"]
        if body.case_id != bundle["descriptor"]["case_id"] or body.card_id != view["card_id"] or body.source_bundle_sha256 != bundle["manifest_sha256"] or body.source_semantic_sha256 != bundle["semantic_sha256"]:
            raise ValueError("review_source_identity_mismatch")
        return reviews.create(view["card_id"], bundle["manifest_sha256"], body.case_id, bundle["semantic_sha256"])

    @app.patch("/api/console/v1/reviews/{review_id}/progress")
    async def review_progress(review_id: str, body: ReviewProgress): return reviews.update_progress(review_id, body.current_step, body.completed_step_ids, body.unresolved_item_ids)

    def _validate_entity(entity_type: str, token: str) -> None:
        fields = {"fact":"observed_facts","relation":None,"gap":"gaps","hypothesis":"hypotheses","comparison":"comparisons","question":"questions"}
        for case_token in cases.tokens:
            view = cases.get(case_token)["console_view"]
            if entity_type == "fact" and any(x["fact_id"] == token for x in view["card"]["observed_facts"]): return
            if entity_type == "relation" and any(x["id"] == token for x in view["graph"]["edges"]): return
            id_keys = {"gap":"gap_id","hypothesis":"hypothesis_id","comparison":"comparison_id","question":"analyst_question_id"}
            if entity_type in id_keys and any(x[id_keys[entity_type]] == token for x in view[fields[entity_type]]): return
        raise KeyError("unknown_entity_token")

    async def _item_state(review_id: str, entity_type: str, token: str, body: ReviewItemState):
        _validate_entity(entity_type, token); return reviews.set_item_state(review_id, entity_type, token, body.state)

    @app.post("/api/console/v1/reviews/{review_id}/facts/{token}/state")
    async def fact_state(review_id: str, token: str, body: ReviewItemState): return await _item_state(review_id,"fact",token,body)
    @app.post("/api/console/v1/reviews/{review_id}/relations/{token}/state")
    async def relation_state(review_id: str, token: str, body: ReviewItemState): return await _item_state(review_id,"relation",token,body)
    @app.post("/api/console/v1/reviews/{review_id}/gaps/{token}/state")
    async def gap_state(review_id: str, token: str, body: ReviewItemState): return await _item_state(review_id,"gap",token,body)
    @app.post("/api/console/v1/reviews/{review_id}/hypotheses/{token}/state")
    async def hypothesis_state(review_id: str, token: str, body: ReviewItemState): return await _item_state(review_id,"hypothesis",token,body)
    @app.post("/api/console/v1/reviews/{review_id}/comparisons/{token}/state")
    async def comparison_state(review_id: str, token: str, body: ReviewItemState): return await _item_state(review_id,"comparison",token,body)
    @app.post("/api/console/v1/reviews/{review_id}/questions/{token}/state")
    async def question_state(review_id: str, token: str, body: ReviewItemState): return await _item_state(review_id,"question",token,body)
    @app.post("/api/console/v1/reviews/{review_id}/complete")
    async def review_complete(review_id: str, body: ReviewComplete): return reviews.complete(review_id, body.operator_summary, body.next_manual_step, body.limitations)
    @app.post("/api/console/v1/reviews/{review_id}/export")
    async def review_export(review_id: str): return reviews.export(review_id)
    @app.get("/api/console/v1/reviews/{review_id}/history")
    async def review_history(review_id: str): return reviews.history(review_id)

    @app.get("/api/console/v1/entities/{entity_token}/links")
    async def entity_links(entity_token: str):
        for case_token in cases.tokens:
            view = cases.get(case_token)["console_view"]
            haystack = [x["fact_id"] for x in view["card"]["observed_facts"]] + [x["gap_id"] for x in view["gaps"]] + [x["hypothesis_id"] for x in view["hypotheses"]]
            if entity_token in haystack: return {"entity_token":entity_token,"case_token":case_token,"links":[f"/ui/cases/{case_token}/timeline?focus={entity_token}",f"/ui/cases/{case_token}/graph?focus={entity_token}"]}
        raise HTTPException(404)
    @app.get("/api/console/v1/relations/{relation_token}/explanation")
    async def relation_explanation(relation_token: str):
        _validate_entity("relation", relation_token)
        for case_token in cases.tokens:
            edge = next((x for x in cases.get(case_token)["console_view"]["graph"]["edges"] if x["id"] == relation_token), None)
            if edge: return {"schema_version":"graph_entity_explanation_v1",**edge,"plain_name":"Структурное или временное отношение; не причинность."}
        raise HTTPException(404)
    @app.get("/api/console/v1/comparisons/{comparison_token}/explanation")
    async def comparison_explanation(comparison_token: str):
        _validate_entity("comparison", comparison_token)
        for case_token in cases.tokens:
            item = next((x for x in cases.get(case_token)["console_view"]["comparisons"] if x["comparison_id"] == comparison_token), None)
            if item: return item
        raise HTTPException(404)
    @app.get("/api/console/v1/tasks")
    async def tasks(): return list(catalog.tasks.values())
    @app.post("/api/console/v1/tasks/{task_id}/runs")
    async def task_run(task_id: str, body: TaskStart): return runner.run(task_id, confirmed=body.confirmed)
    @app.get("/api/console/v1/runs")
    async def runs(): return runner.list()
    @app.get("/api/console/v1/runs/{run_id}")
    async def run_get(run_id: str): return runner.get(run_id)
    @app.post("/api/console/v1/runs/{run_id}/cancel")
    async def run_cancel(run_id: str): return runner.cancel(run_id)
    @app.get("/api/console/v1/runs/{run_id}/log", response_class=PlainTextResponse)
    async def run_log(run_id: str): return runner.log(run_id)
    @app.get("/api/console/v1/audit")
    async def audit(): return db.audits()
    @app.get("/api/console/v1/system")
    async def system(): return {"python": __import__("platform").python_version(), "platform": __import__("platform").system(), "runtime_token": "runtime/lab_console", "task_count": len(catalog.tasks)}
    @app.get("/api/console/v1/files/{file_token}")
    async def file_view(file_token: str): return read_safe(file_token, settings.max_view_bytes)
    return app


def _bundle(token):
    mapping = {"v040": "ml/reports/v0_4_0/v0_4_0_bundle_manifest.json", "v041": "ml/reports/v0_4_1/v0_4_1_bundle_manifest.json", "v042": "ml/reports/v0_4_2/v0_4_2_bundle_manifest.json"}
    if token not in mapping: raise HTTPException(404)
    return load_source(mapping[token])


def _card_part(token, part):
    if token != "representative": raise HTTPException(404)
    return build_console_view()[part]

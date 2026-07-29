from __future__ import annotations

import json
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
from .models import (CandidateProposalCreate, CandidateProposalReviewComplete,
                     CandidateProposalReviewNote, CandidateProposalReviewProgress,
                     ComparisonReviewNote, ComparisonReviewPatch, LaboratoryRunCreate,
                     LaboratoryRunExecute, LaboratoryRunRecovery, ReviewCheck,
                     ReviewComplete, ReviewCreate, ReviewDecision, ReviewItemState,
                     ReviewNote, ReviewProgress, RunComparisonCreate, TaskStart,
                     ProposalTrainingRecovery, ProposalTrainingStart,
                     BlindValidationCreate, BlindInferenceStart, BlindInferenceRecovery,
                     BlindValidationReviewProgress, BlindValidationReviewNote,
                     BlindValidationReviewComplete)
from .candidate_proposals import CandidateProposalService
from .blind_validations import BlindValidationService
from .corrective_cycles import failure_analysis
from .lab_runs import LaboratoryRunService
from .presentation import NAVIGATION, present_page
from .presentation.views import TITLE, incident as present_incident
from .presentation.statuses import status_display, status_label
from .presentation.case_views import case_catalog, case_page
from .review import ReviewService
from .security import SessionStore

PAGES = {key: value for key, value in TITLE.items() if key not in {"cases", "lab-runs", "run-comparisons", "candidate-proposals", "candidate-versions", "blind-validations"}}


def create_app(settings: Settings | None = None, database_path: Path | None = None) -> FastAPI:
    settings = settings or load_settings()
    runtime = settings.runtime_dir
    db = Database(database_path or runtime / "console.sqlite3"); db.migrate()
    task_catalog_path = Path(__file__).parent / "jobs" / "allowed_tasks_v2.yaml"
    catalog = TaskCatalog(task_catalog_path if task_catalog_path.is_file() else Path(__file__).parent / "jobs" / "allowed_tasks_v1.yaml")
    ui_catalog = TaskCatalog(Path(__file__).parent / "jobs" / "allowed_tasks_v1.yaml")
    runner = TaskRunner(catalog, db, runtime, settings.max_parallel_tasks)
    reviews = ReviewService(db); cases = CaseRegistry(); lab_runs = LaboratoryRunService(db, runtime, cases); proposals = CandidateProposalService(db, runtime); blind_validations = BlindValidationService(db, runtime); sessions = SessionStore(settings.token, settings.session_ttl_seconds)
    app = FastAPI(title="Филин — лабораторная консоль", version="0.4.7", docs_url=None, redoc_url=None)
    templates = Jinja2Templates(directory=Path(__file__).parent / "templates")
    templates.env.filters["json_ru"] = lambda value: json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)
    templates.env.filters["status_label"] = status_label
    templates.env.filters["status_display"] = status_display
    app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")
    app.state.settings, app.state.db, app.state.catalog, app.state.runner, app.state.cases, app.state.reviews, app.state.lab_runs, app.state.proposals, app.state.blind_validations = settings, db, catalog, runner, cases, reviews, lab_runs, proposals, blind_validations

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
        if page == "candidate-proposals":
            context = {**present_page("models", reviews, runner, ui_catalog), "request": request, "csrf": request.state.session.csrf, "page": page,
                       "title": "Предложения кандидатов", "breadcrumbs": ["Филин", "Предложения кандидатов"], "proposals": proposals.list(),
                       "data_catalog": proposals.data_catalog(), "splits": proposals.splits(), "recipes": proposals.recipes(), "criteria": proposals.admission_criteria()}
            return templates.TemplateResponse(request, "pages/candidate_proposals.html", context)
        if page == "blind-validations":
            context = {**present_page("models", reviews, runner, ui_catalog), "request": request, "csrf": request.state.session.csrf,
                       "page": page, "title": "Слепые лабораторные проверки", "breadcrumbs": ["Филин", "Слепые лабораторные проверки"],
                       "validations": blind_validations.list(), "roles": blind_validations.roles()}
            return templates.TemplateResponse(request, "pages/blind_validations.html", context)
        if page == "failure-analysis":
            analysis = failure_analysis()
            context = {**present_page("models", reviews, runner, ui_catalog), "request": request,
                       "csrf": request.state.session.csrf, "page": page, "title": "Разбор отрицательного результата",
                       "breadcrumbs": ["Филин", "Разбор отрицательного результата"], "analysis": analysis,
                       "view_model": "failure_analysis_v0471"}
            return templates.TemplateResponse(request, "pages/failure_analysis.html", context)
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

    @app.get("/ui/failure-analysis/{view}", response_class=HTMLResponse)
    async def failure_analysis_page(request: Request, view: str):
        try:
            analysis = failure_analysis(view)
        except KeyError:
            raise HTTPException(404)
        context = {**present_page("models", reviews, runner, ui_catalog), "request": request,
                   "csrf": request.state.session.csrf, "page": "failure-analysis", "title": "Разбор отрицательного результата",
                   "breadcrumbs": ["Филин", "Разбор отрицательного результата", view], "analysis": analysis,
                   "view_model": "failure_analysis_v0471"}
        return templates.TemplateResponse(request, "pages/failure_analysis.html", context)

    @app.get("/api/console/v1/failure-analysis/{view}")
    async def failure_analysis_api(view: str):
        try:
            return failure_analysis(view)
        except KeyError:
            raise HTTPException(404)

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

    @app.get("/ui/candidate-proposals/{proposal_token}", response_class=HTMLResponse)
    async def candidate_proposal_detail_page(request: Request, proposal_token: str):
        try: proposal = proposals.get(proposal_token)
        except (KeyError, ValueError): raise HTTPException(404)
        context = {**present_page("models", reviews, runner, ui_catalog), "request": request, "csrf": request.state.session.csrf, "page": "candidate-proposals",
                   "title": "Предложение лабораторного кандидата", "breadcrumbs": ["Филин", "Предложения кандидатов", proposal["proposal_id"]],
                   "proposal": proposal, "training_runs": proposals.training_runs(proposal_token), "compatibility": proposals.compatibility(proposal_token),
                   "criteria": proposals.admission_criteria()}
        return templates.TemplateResponse(request, "pages/candidate_proposal_detail.html", context)

    @app.get("/ui/candidate-proposal-reviews/{review_id}", response_class=HTMLResponse)
    async def candidate_proposal_review_page(request: Request, review_id: str):
        try: review = proposals.review(review_id); proposal = proposals.get(review["proposal_token"])
        except (KeyError, ValueError): raise HTTPException(404)
        context = {**present_page("reviews", reviews, runner, ui_catalog), "request": request, "csrf": request.state.session.csrf, "page": "candidate-proposals",
                   "title": "Рассмотреть предложение лабораторного кандидата", "breadcrumbs": ["Филин", "Предложения кандидатов", "Ручное рассмотрение"],
                   "proposal": proposal, "proposal_review": review}
        return templates.TemplateResponse(request, "pages/candidate_proposal_review.html", context)

    blind_views = [
        ("overview", "Обзор"), ("control-packs", "Контрольные наборы"), ("commitments", "Предварительная фиксация"),
        ("roles", "Роли и доступ"), ("blindness", "Сохранение слепого режима"), ("prediction-plans", "Планы формирования прогнозов"),
        ("active-inference", "Применение действующего кандидата"), ("proposal-inference", "Применение предложения кандидата"),
        ("prediction-commitments", "Фиксация пакетов прогнозов"), ("label-unlock", "Раскрытие разметки"),
        ("evaluation", "Оценка"), ("comparability", "Сопоставимость"), ("metrics", "Показатели"),
        ("classes", "Классы"), ("episodes", "Эпизоды"), ("abstentions", "Отказы от решения"),
        ("reconstruction", "Реконструкция"), ("cards", "Карточки"), ("gaps", "Разрывы"),
        ("hypotheses", "Гипотезы"), ("differences", "Различия"), ("acceptance-gate", "Критерии приёмки"),
        ("manual-review", "Ручное рассмотрение"), ("export", "Экспорт"), ("limitations", "Ограничения"),
    ]

    @app.get("/ui/blind-validations/{validation_token}", response_class=HTMLResponse)
    @app.get("/ui/blind-validations/{validation_token}/{view}", response_class=HTMLResponse)
    async def blind_validation_detail_page(request: Request, validation_token: str, view: str = "overview"):
        if view not in dict(blind_views): raise HTTPException(404)
        try: validation = blind_validations.get(validation_token)
        except (KeyError, ValueError): raise HTTPException(404)
        evaluation = validation.get("evaluation") or {}
        comparison = validation.get("comparison") or {}
        participants = evaluation.get("participants", {})
        view_data = {
            "overview": {k: validation.get(k) for k in ("validation_lineage_id", "proposal_id", "active_candidate_id", "status", "protocol_revision", "independence_assessment", "final_decision")},
            "control-packs": validation.get("control_pack"), "commitments": {"label": validation.get("label_commitment"), "predictions": validation.get("prediction_commitments")},
            "roles": validation.get("role_assignments"), "blindness": {"overlap": validation.get("overlap_assessment"), "blindness": validation.get("blindness_gate")},
            "prediction-plans": validation.get("prediction_plan"), "active-inference": [x for x in validation.get("inference_runs", []) if x.get("participant") == "active_candidate"],
            "proposal-inference": [x for x in validation.get("inference_runs", []) if x.get("participant") == "proposal"],
            "prediction-commitments": validation.get("prediction_commitments"), "label-unlock": {"status": validation.get("label_status"), "unlock": validation.get("label_unlock")},
            "evaluation": evaluation, "comparability": comparison.get("comparability"), "metrics": participants,
            "classes": {k: v.get("class_metrics", []) for k, v in participants.items()},
            "episodes": {k: {m: v.get(m) for m in ("episode_recall", "episode_precision", "detection_delay_seconds")} for k, v in participants.items()},
            "abstentions": {k: {m: v.get(m) for m in ("abstention_rate", "missing_predictions", "duplicate_predictions", "invalid_predictions")} for k, v in participants.items()},
            "reconstruction": comparison.get("reconstruction_differences"), "cards": comparison.get("card_differences"),
            "gaps": comparison.get("gap_differences"), "hypotheses": comparison.get("hypothesis_differences"),
            "differences": comparison, "acceptance-gate": validation.get("acceptance_result") or validation.get("acceptance_definition"),
            "manual-review": {"review_id": validation.get("review_id"), "final_decision": validation.get("final_decision")},
            "export": {"available": bool(validation.get("review_id")), "runtime_only": True, "contains_model_or_dataset": False},
            "limitations": validation.get("limitations"),
        }[view]
        context = {**present_page("models", reviews, runner, ui_catalog), "request": request, "csrf": request.state.session.csrf,
                   "page": "blind-validations", "title": "Слепая лабораторная проверка",
                   "breadcrumbs": ["Филин", "Слепые проверки", validation_token], "validation": validation,
                   "blind_views": blind_views, "blind_view": view, "blind_view_title": dict(blind_views)[view], "blind_view_data": view_data}
        return templates.TemplateResponse(request, "pages/blind_validation_detail.html", context)

    @app.get("/ui/blind-validation-reviews/{review_id}", response_class=HTMLResponse)
    async def blind_validation_review_page(request: Request, review_id: str):
        try:
            review = blind_validations.review(review_id)
            validation = blind_validations.get(review["validation_token"])
        except (KeyError, ValueError): raise HTTPException(404)
        context = {**present_page("reviews", reviews, runner, ui_catalog), "request": request, "csrf": request.state.session.csrf,
                   "page": "blind-validations", "title": "Ручное рассмотрение слепой проверки",
                   "breadcrumbs": ["Филин", "Слепые проверки", "Ручное рассмотрение"],
                   "blind_review": review, "validation": validation}
        return templates.TemplateResponse(request, "pages/blind_validation_review.html", context)

    @app.get("/api/console/v1/health")
    async def health(): return {"schema_version": "console_health_v1", "status": "ok", "laboratory_only": True}

    def blind_auth(request: Request, roles: set[str], operation: str) -> str:
        return blind_validations.authorize(request.headers.get("x-blind-role-token"), roles, operation)

    @app.get("/api/console/v1/blind-validations")
    async def blind_validation_catalog(): return blind_validations.list()
    @app.get("/api/console/v1/blind-validations/control-packs")
    async def blind_control_pack_catalog(): return blind_validations.control_packs()
    @app.get("/api/console/v1/blind-validations/roles")
    async def blind_role_catalog(): return blind_validations.roles()
    @app.post("/api/console/v1/blind-validations")
    async def blind_validation_create(request: Request, body: BlindValidationCreate):
        blind_auth(request, {"control_data_custodian"}, "create_control_pack")
        if not body.confirmed: raise ValueError("confirmation_required")
        return blind_validations.create()
    @app.get("/api/console/v1/blind-validations/{validation_token}")
    async def blind_validation_get(validation_token: str): return blind_validations.get(validation_token)
    @app.get("/api/console/v1/blind-validations/{validation_token}/protocol")
    async def blind_validation_protocol(validation_token: str): return blind_validations.protocol(validation_token)
    @app.get("/api/console/v1/blind-validations/{validation_token}/control-pack")
    async def blind_validation_control_pack(validation_token: str): return blind_validations.get(validation_token)["control_pack"]
    @app.get("/api/console/v1/blind-validations/{validation_token}/commitments")
    async def blind_validation_commitments(validation_token: str):
        value = blind_validations.get(validation_token)
        return {"label_commitment": value["label_commitment"], "prediction_commitments": value["prediction_commitments"]}
    @app.get("/api/console/v1/blind-validations/{validation_token}/blindness")
    async def blind_validation_blindness(validation_token: str): return blind_validations.get(validation_token)["blindness_gate"]
    @app.get("/api/console/v1/blind-validations/{validation_token}/prediction-plan")
    async def blind_validation_prediction_plan(validation_token: str): return blind_validations.get(validation_token)["prediction_plan"]
    @app.get("/api/console/v1/blind-validations/{validation_token}/predictions")
    async def blind_validation_predictions(validation_token: str):
        value = blind_validations.get(validation_token)
        return {"inference_runs": value["inference_runs"], "prediction_commitments": value["prediction_commitments"], "prediction_rows_exposed": False}
    @app.get("/api/console/v1/blind-validations/{validation_token}/label-status")
    async def blind_validation_label_status(validation_token: str): return blind_validations.get(validation_token)["label_status"]
    @app.get("/api/console/v1/blind-validations/{validation_token}/evaluation")
    async def blind_validation_evaluation(validation_token: str): return blind_validations.get(validation_token)["evaluation"]
    @app.get("/api/console/v1/blind-validations/{validation_token}/comparison")
    async def blind_validation_comparison(validation_token: str): return blind_validations.get(validation_token)["comparison"]
    @app.get("/api/console/v1/blind-validations/{validation_token}/gate")
    async def blind_validation_gate(validation_token: str): return blind_validations.get(validation_token)["acceptance_result"]
    @app.get("/api/console/v1/blind-validations/{validation_token}/review")
    async def blind_validation_review_get(validation_token: str):
        value = blind_validations.get(validation_token)
        return blind_validations.review(value["review_id"]) if value.get("review_id") else None

    @app.post("/api/console/v1/blind-validations/{validation_token}/validate")
    async def blind_validation_validate(request: Request, validation_token: str): blind_auth(request, {"control_data_custodian"}, "create_control_pack"); return blind_validations.validate(validation_token)
    @app.post("/api/console/v1/blind-validations/{validation_token}/commit-control-pack")
    async def blind_validation_commit_control(request: Request, validation_token: str): blind_auth(request, {"control_data_custodian"}, "commit_labels"); return blind_validations.get(validation_token)["label_commitment"]
    @app.post("/api/console/v1/blind-validations/{validation_token}/check-overlap")
    async def blind_validation_overlap(request: Request, validation_token: str): blind_auth(request, {"control_data_custodian"}, "create_control_pack"); return blind_validations.check_overlap(validation_token)
    @app.post("/api/console/v1/blind-validations/{validation_token}/check-blindness")
    async def blind_validation_check_blindness(request: Request, validation_token: str): blind_auth(request, {"inference_operator"}, "check_blindness"); return blind_validations.check_blindness(validation_token)
    @app.post("/api/console/v1/blind-validations/{validation_token}/freeze-plan")
    async def blind_validation_freeze_plan(request: Request, validation_token: str): blind_auth(request, {"inference_operator"}, "freeze_plan"); return blind_validations.freeze_plan(validation_token)
    @app.post("/api/console/v1/blind-validations/{validation_token}/run-active")
    async def blind_validation_run_active(request: Request, validation_token: str, body: BlindInferenceStart): blind_auth(request, {"inference_operator"}, "run_active"); return blind_validations.run_active(validation_token, interrupt=body.interrupt)
    @app.post("/api/console/v1/blind-validations/{validation_token}/run-proposal")
    async def blind_validation_run_proposal(request: Request, validation_token: str, body: BlindInferenceStart): blind_auth(request, {"inference_operator"}, "run_proposal"); return blind_validations.run_proposal(validation_token, interrupt=body.interrupt)
    @app.post("/api/console/v1/blind-validations/{validation_token}/recover-run")
    async def blind_validation_recover(request: Request, validation_token: str, body: BlindInferenceRecovery): blind_auth(request, {"inference_operator"}, "recover_run"); return blind_validations.recover_run(validation_token, body.execution_id)
    @app.post("/api/console/v1/blind-validations/{validation_token}/freeze-predictions")
    async def blind_validation_freeze_predictions(request: Request, validation_token: str): blind_auth(request, {"inference_operator"}, "freeze_predictions"); return blind_validations.freeze_predictions(validation_token)
    @app.post("/api/console/v1/blind-validations/{validation_token}/authorize-label-unlock")
    async def blind_validation_authorize_unlock(request: Request, validation_token: str): blind_auth(request, {"control_data_custodian"}, "authorize_unlock"); return blind_validations.authorize_label_unlock(validation_token)
    @app.post("/api/console/v1/blind-validations/{validation_token}/unlock-labels")
    async def blind_validation_unlock(request: Request, validation_token: str): blind_auth(request, {"evaluation_operator"}, "unlock_labels"); return blind_validations.unlock_labels(validation_token)
    @app.post("/api/console/v1/blind-validations/{validation_token}/evaluate")
    async def blind_validation_evaluate(request: Request, validation_token: str): blind_auth(request, {"evaluation_operator"}, "evaluate"); return blind_validations.evaluate(validation_token)
    @app.post("/api/console/v1/blind-validations/{validation_token}/compare")
    async def blind_validation_compare(request: Request, validation_token: str): blind_auth(request, {"evaluation_operator"}, "compare"); return blind_validations.compare(validation_token)
    @app.post("/api/console/v1/blind-validations/{validation_token}/reviews")
    async def blind_validation_review_create(request: Request, validation_token: str): blind_auth(request, {"validation_reviewer"}, "review"); return blind_validations.create_review(validation_token)
    @app.patch("/api/console/v1/blind-validation-reviews/{review_id}/progress")
    async def blind_validation_review_progress(request: Request, review_id: str, body: BlindValidationReviewProgress): blind_auth(request, {"validation_reviewer"}, "review"); return blind_validations.update_review(review_id, completed_steps=body.completed_steps)
    @app.post("/api/console/v1/blind-validation-reviews/{review_id}/notes")
    async def blind_validation_review_note(request: Request, review_id: str, body: BlindValidationReviewNote): blind_auth(request, {"validation_reviewer"}, "review"); return blind_validations.update_review(review_id, note=body.text)
    @app.post("/api/console/v1/blind-validation-reviews/{review_id}/decision")
    @app.post("/api/console/v1/blind-validation-reviews/{review_id}/complete")
    async def blind_validation_review_complete(request: Request, review_id: str, body: BlindValidationReviewComplete): blind_auth(request, {"validation_reviewer"}, "decide"); return blind_validations.complete_review(review_id, body.decision, body.reviewer_summary)
    @app.post("/api/console/v1/blind-validations/{validation_token}/export")
    async def blind_validation_export(request: Request, validation_token: str): blind_auth(request, {"validation_reviewer"}, "export"); return blind_validations.export(validation_token)

    @app.get("/api/console/v1/candidate-proposals")
    async def candidate_proposal_catalog(): return proposals.list()
    @app.get("/api/console/v1/candidate-proposals/data-catalog")
    async def candidate_proposal_data_catalog(): return proposals.data_catalog()
    @app.get("/api/console/v1/candidate-proposals/splits")
    async def candidate_proposal_splits(): return proposals.splits()
    @app.get("/api/console/v1/candidate-proposals/recipes")
    async def candidate_proposal_recipes(): return proposals.recipes()
    @app.get("/api/console/v1/candidate-proposals/admission-criteria")
    async def candidate_proposal_admission_criteria(): return proposals.admission_criteria()
    @app.post("/api/console/v1/candidate-proposals")
    async def candidate_proposal_create(body: CandidateProposalCreate): return proposals.create(body.data_catalog_id, body.split_id, body.recipe_id)
    @app.get("/api/console/v1/candidate-proposals/{proposal_token}")
    async def candidate_proposal_get(proposal_token: str): return proposals.get(proposal_token)
    @app.get("/api/console/v1/candidate-proposals/{proposal_token}/lineage")
    async def candidate_proposal_lineage(proposal_token: str):
        p = proposals.get(proposal_token); return {"schema_version": "candidate_proposal_lineage_v1", "proposal_id": p["proposal_id"], "candidate_id": None, "parent_proposal_id": None, "screening_feedback_reused": False}
    @app.get("/api/console/v1/candidate-proposals/{proposal_token}/leakage")
    async def candidate_proposal_leakage(proposal_token: str): proposals.get(proposal_token); return proposals.leakage_assessment()
    @app.get("/api/console/v1/candidate-proposals/{proposal_token}/training-runs")
    async def candidate_proposal_training_runs(proposal_token: str): return proposals.training_runs(proposal_token)
    @app.get("/api/console/v1/candidate-proposals/{proposal_token}/artifact")
    async def candidate_proposal_artifact(proposal_token: str):
        p = proposals.get(proposal_token); return {"schema_version": "model_artifact_descriptor_v1", "artifact_sha256": p["model_artifact_sha256"], "semantic_sha256": p["model_semantic_sha256"], "runtime_only": True, "distribution_allowed": False, "license_status": p["license_status"]}
    @app.get("/api/console/v1/candidate-proposals/{proposal_token}/reproducibility")
    async def candidate_proposal_reproducibility(proposal_token: str): return proposals.get(proposal_token).get("reproducibility_assessment")
    @app.get("/api/console/v1/candidate-proposals/{proposal_token}/compatibility")
    async def candidate_proposal_compatibility(proposal_token: str): return proposals.compatibility(proposal_token)
    @app.get("/api/console/v1/candidate-proposals/{proposal_token}/screening")
    async def candidate_proposal_screening(proposal_token: str): return proposals.get(proposal_token).get("screening")
    @app.get("/api/console/v1/candidate-proposals/{proposal_token}/comparison")
    async def candidate_proposal_comparison(proposal_token: str): return proposals.get(proposal_token).get("comparison")
    @app.get("/api/console/v1/candidate-proposals/{proposal_token}/gate")
    async def candidate_proposal_gate(proposal_token: str): return proposals.get(proposal_token).get("gate_result")
    @app.get("/api/console/v1/candidate-proposals/{proposal_token}/review")
    async def candidate_proposal_review_get(proposal_token: str):
        p = proposals.get(proposal_token); return proposals.review(p["review_id"]) if p.get("review_id") else None
    @app.post("/api/console/v1/candidate-proposals/{proposal_token}/validate")
    async def candidate_proposal_validate(proposal_token: str): return proposals.validate(proposal_token)
    @app.post("/api/console/v1/candidate-proposals/{proposal_token}/dry-run")
    async def candidate_proposal_dry_run(proposal_token: str): return proposals.dry_run(proposal_token)
    @app.post("/api/console/v1/candidate-proposals/{proposal_token}/train")
    async def candidate_proposal_train(proposal_token: str, body: ProposalTrainingStart):
        if not body.confirmed: raise ValueError("confirmation_required")
        return proposals.train(proposal_token)
    @app.post("/api/console/v1/candidate-proposals/{proposal_token}/cancel-training")
    async def candidate_proposal_cancel_training(proposal_token: str): return proposals.cancel_training(proposal_token)
    @app.post("/api/console/v1/candidate-proposals/{proposal_token}/recover-training")
    async def candidate_proposal_recover_training(proposal_token: str, body: ProposalTrainingRecovery): return proposals.recover_training(proposal_token, body.execution_id, body.action)
    @app.post("/api/console/v1/candidate-proposals/{proposal_token}/verify-reproducibility")
    async def candidate_proposal_verify_reproducibility(proposal_token: str): return proposals.verify_reproducibility(proposal_token)
    @app.post("/api/console/v1/candidate-proposals/{proposal_token}/freeze")
    async def candidate_proposal_freeze(proposal_token: str): return proposals.freeze(proposal_token)
    @app.post("/api/console/v1/candidate-proposals/{proposal_token}/screen")
    async def candidate_proposal_screen(proposal_token: str): return proposals.screen(proposal_token)
    @app.post("/api/console/v1/candidate-proposals/{proposal_token}/compare")
    async def candidate_proposal_compare(proposal_token: str): return proposals.compare(proposal_token)
    @app.post("/api/console/v1/candidate-proposals/{proposal_token}/reviews")
    async def candidate_proposal_review_create(proposal_token: str): return proposals.create_review(proposal_token)
    @app.post("/api/console/v1/candidate-proposals/{proposal_token}/export")
    async def candidate_proposal_export(proposal_token: str): return proposals.export(proposal_token)
    @app.patch("/api/console/v1/candidate-proposal-reviews/{review_id}/progress")
    async def candidate_proposal_review_progress(review_id: str, body: CandidateProposalReviewProgress): return proposals.update_review(review_id, completed_steps=body.completed_steps)
    @app.post("/api/console/v1/candidate-proposal-reviews/{review_id}/notes")
    async def candidate_proposal_review_note(review_id: str, body: CandidateProposalReviewNote): return proposals.update_review(review_id, note=body.text)
    @app.post("/api/console/v1/candidate-proposal-reviews/{review_id}/decision")
    async def candidate_proposal_review_decision(review_id: str, body: CandidateProposalReviewComplete): return proposals.complete_review(review_id, body.decision, body.reviewer_summary, body.limitations, body.next_allowed_action)
    @app.post("/api/console/v1/candidate-proposal-reviews/{review_id}/complete")
    async def candidate_proposal_review_complete(review_id: str, body: CandidateProposalReviewComplete): return proposals.complete_review(review_id, body.decision, body.reviewer_summary, body.limitations, body.next_allowed_action)

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

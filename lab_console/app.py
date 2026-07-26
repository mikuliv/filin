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
from .config import Settings, load_settings
from .database import Database
from .files import read_safe
from .jobs import TaskCatalog, TaskRunner
from .models import ReviewCheck, ReviewCreate, ReviewDecision, ReviewNote, TaskStart
from .review import ReviewService
from .security import SessionStore

PAGES = {
    "dashboard": "Главная панель", "stages": "Этапы проекта", "models": "Модели",
    "metrics": "Результаты модели", "bundles": "Комплекты и артефакты", "incidents": "Карточки инцидентов",
    "timeline": "Временная шкала", "graph": "Граф реконструкции", "hypotheses": "Конкурирующие гипотезы",
    "comparisons": "Матрица сопоставлений", "questions": "Вопросы специалисту", "reviews": "Ручное рассмотрение",
    "tasks": "Запуски и задачи", "tests": "Тесты", "logs": "Журналы", "system": "Состояние системы",
}


def create_app(settings: Settings | None = None, database_path: Path | None = None) -> FastAPI:
    settings = settings or load_settings()
    runtime = settings.runtime_dir
    db = Database(database_path or runtime / "console.sqlite3"); db.migrate()
    catalog = TaskCatalog(Path(__file__).parent / "jobs" / "allowed_tasks_v1.yaml")
    runner = TaskRunner(catalog, db, runtime, settings.max_parallel_tasks)
    reviews = ReviewService(db); sessions = SessionStore(settings.token, settings.session_ttl_seconds)
    app = FastAPI(title="Филин — лабораторная консоль", version="0.4.3", docs_url=None, redoc_url=None)
    templates = Jinja2Templates(directory=Path(__file__).parent / "templates")
    app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")
    app.state.settings, app.state.db, app.state.catalog, app.state.runner = settings, db, catalog, runner

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
        response = RedirectResponse("/", 303)
        response.set_cookie("filin_session", sid, httponly=True, samesite="strict", secure=False, max_age=settings.session_ttl_seconds, path="/")
        return response

    @app.post("/api/console/v1/logout")
    async def logout(request: Request):
        sessions.revoke(request.cookies.get("filin_session")); response = JSONResponse({"logged_out": True})
        response.delete_cookie("filin_session", path="/"); return response

    @app.get("/", response_class=HTMLResponse)
    async def dashboard(request: Request):
        return templates.TemplateResponse(request, "page.html", _context(request, "dashboard", project_status()))

    @app.get("/ui/{page}", response_class=HTMLResponse)
    async def page(request: Request, page: str):
        if page not in PAGES: raise HTTPException(404)
        data = _page_data(page, reviews, runner, catalog)
        return templates.TemplateResponse(request, "page.html", _context(request, page, data))

    @app.get("/api/console/v1/health")
    async def health(): return {"schema_version": "console_health_v1", "status": "ok", "laboratory_only": True}
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
    async def cards(): return [{"card_token": "representative", **build_incident_card_v2()}]
    @app.get("/api/console/v1/incident-cards/{card_token}")
    async def card(card_token: str): return _card_part(card_token, "card")
    @app.get("/api/console/v1/incident-cards/{card_token}/{part}")
    async def card_part(card_token: str, part: str):
        if part not in {"timeline", "graph", "hypotheses", "questions"}: raise HTTPException(404)
        return _card_part(card_token, part)
    @app.get("/api/console/v1/reviews")
    async def review_list(): return reviews.list()
    @app.post("/api/console/v1/reviews")
    async def review_create(body: ReviewCreate): return reviews.create(body.card_id, body.source_sha256)
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
    async def review_decision(review_id: str, body: ReviewDecision): return reviews.decide(review_id, body.status, body.limitations, body.next_manual_step)
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


def _context(request: Request, page: str, data):
    return {"request": request, "title": PAGES[page], "page": page, "pages": PAGES, "data": json.dumps(data, ensure_ascii=False, indent=2, default=str), "csrf": request.state.session.csrf}


def _page_data(page, reviews, runner, catalog):
    if page == "reviews": return reviews.list()
    if page in {"tasks", "logs"}: return {"tasks": list(catalog.tasks.values()), "runs": runner.list()}
    if page == "incidents": return build_incident_card_v2()
    if page in {"timeline", "graph", "hypotheses", "comparisons", "questions"}: return build_console_view().get(page)
    if page == "bundles": return [_bundle(f"v04{n}") for n in range(3)]
    return project_status()


def _bundle(token):
    mapping = {"v040": "ml/reports/v0_4_0/v0_4_0_bundle_manifest.json", "v041": "ml/reports/v0_4_1/v0_4_1_bundle_manifest.json", "v042": "ml/reports/v0_4_2/v0_4_2_bundle_manifest.json"}
    if token not in mapping: raise HTTPException(404)
    return load_source(mapping[token])


def _card_part(token, part):
    if token != "representative": raise HTTPException(404)
    return build_console_view()[part]

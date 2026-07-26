from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from lab_console.app import PAGES, create_app
from lab_console.cards import build_console_view, build_incident_card_v2
from lab_console.config import ROOT, Settings
from lab_console.database import Database
from lab_console.files import read_safe, resolve_token, token_for
from lab_console.integrity import semantic_sha
from lab_console.jobs import TaskCatalog, TaskRunner
from lab_console.review import ReviewService
from lab_console.security import SessionStore, redact


@pytest.fixture()
def client(tmp_path):
    app = create_app(Settings(token="correct-long-local-token", runtime_dir=tmp_path), tmp_path / "console.sqlite3")
    with TestClient(app) as value:
        yield value


def login(client):
    response = client.post("/login", content="token=correct-long-local-token", headers={"content-type": "application/x-www-form-urlencoded"}, follow_redirects=False)
    assert response.status_code == 303
    page = client.get("/")
    csrf = page.text.split('data-csrf="', 1)[1].split('"', 1)[0]
    return csrf


def test_default_and_external_bind_policy():
    assert Settings(token="x").host == "127.0.0.1"
    with pytest.raises(ValueError, match="external_bind_rejected"): Settings(host="0.0.0.0", token="x")
    assert Settings(host="0.0.0.0", token="x", development_mode=True).development_mode


def test_authentication_logout_and_headers(client):
    assert client.get("/").history[-1].status_code == 303
    csrf = login(client)
    response = client.get("/api/console/v1/status")
    assert response.status_code == 200 and response.headers["x-frame-options"] == "DENY"
    assert client.post("/api/console/v1/logout", json={}, headers={"x-csrf-token": csrf}).status_code == 200
    assert client.get("/api/console/v1/status").status_code == 401


def test_bad_login_and_rate_limit():
    store = SessionStore("right")
    assert all(store.authenticate("bad", "peer") is None for _ in range(10))
    assert store.authenticate("right", "peer") is None


@pytest.mark.parametrize("page", list(PAGES))
def test_all_pages_local_and_accessible(client, page):
    login(client)
    url = "/" if page == "dashboard" else f"/ui/{page}"
    text = client.get(url).text
    assert client.get(url).status_code == 200
    assert "К содержанию" in text and "https://" not in text and "http://" not in text


def test_status_keeps_tracks_separate(client):
    login(client); value = client.get("/api/console/v1/status").json()
    assert value["mainline_stage"] == "v0.3.18" and value["laboratory_stage"] == "v0.4.3"
    assert value["production_ready"] is False and value["backend_isolated"] is True


@pytest.mark.parametrize("endpoint", ["stages", "models", "reports", "bundles", "incident-cards", "reviews", "tasks", "runs", "audit", "system"])
def test_read_api_endpoints(client, endpoint):
    login(client); assert client.get(f"/api/console/v1/{endpoint}").status_code == 200


@pytest.mark.parametrize("part", ["timeline", "graph", "hypotheses", "questions"])
def test_incident_subresources(client, part):
    login(client); assert client.get(f"/api/console/v1/incident-cards/representative/{part}").status_code == 200


def test_card_v2_deterministic_and_safe():
    left, right = build_incident_card_v2(), build_incident_card_v2()
    assert left == right and left["schema_version"] == "incident_card_v2"
    assert left["hypothesis_count"] == 6 and left["safety"]["forced_winner"] is False
    assert left["safety"]["causal_inference"] is False


def test_console_view_deterministic():
    assert semantic_sha(build_console_view()) == semantic_sha(build_console_view())


def test_review_overlay_does_not_mutate_source(tmp_path):
    source = ROOT / "ml/reports/v0_4_2/representative_hypothesis_bundle.json"
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    db = Database(tmp_path / "db.sqlite3"); db.migrate(); svc = ReviewService(db)
    review = svc.create("card_1", "a" * 64)
    review = svc.add_check(review["review_session_id"], "integrity", True)
    review = svc.add_note(review["review_session_id"], "Нужны дополнительные первичные сведения.")
    review = svc.decide(review["review_session_id"], "reviewed_without_determination", ["Лабораторный пример"], "Проверить первичный журнал вручную")
    export = svc.export(review["review_session_id"])
    assert review["decision"]["no_final_determination"] and review["decision"]["no_automatic_action"]
    assert export["safety"]["source_artifacts_modified"] is False
    assert export == svc.export(review["review_session_id"])
    assert hashlib.sha256(source.read_bytes()).hexdigest() == before


@pytest.mark.parametrize("status", ["attack_confirmed", "compromise_confirmed", "malicious_actor_confirmed", "automatic_response_approved"])
def test_forbidden_review_decisions(tmp_path, status):
    db = Database(tmp_path / f"{status}.sqlite3"); db.migrate(); svc = ReviewService(db)
    review = svc.create("card", "a" * 64)
    with pytest.raises(ValueError, match="forbidden_review_status"): svc.decide(review["review_session_id"], status, [], "manual")


@pytest.mark.parametrize("note", ["<script>alert(1)</script>", "<b>html</b>", "", "x" * 4001])
def test_unsafe_notes_rejected(tmp_path, note):
    db = Database(tmp_path / "n.sqlite3"); db.migrate(); svc = ReviewService(db); review = svc.create("card", "a" * 64)
    with pytest.raises(ValueError, match="unsafe_review_note"): svc.add_note(review["review_session_id"], note)


def test_api_csrf_content_type_and_strict_schema(client):
    csrf = login(client)
    url = "/api/console/v1/reviews"
    body = {"card_id": "card", "source_sha256": "a" * 64}
    assert client.post(url, json=body).status_code == 403
    assert client.post(url, content=json.dumps(body), headers={"x-csrf-token": csrf, "content-type": "text/plain"}).status_code == 415
    assert client.post(url, json={**body, "extra": 1}, headers={"x-csrf-token": csrf}).status_code == 422
    assert client.post(url, json=body, headers={"x-csrf-token": csrf}).status_code == 200


@pytest.mark.parametrize("token", ["Li4vLi4vc2VjcmV0", "L3dpbmRvd3M", "!!", "A" * 1025])
def test_path_traversal_and_bad_tokens_rejected(token):
    with pytest.raises((ValueError, FileNotFoundError)): resolve_token(token)


def test_safe_file_view_and_crlf_normalization(tmp_path):
    path = ROOT / "docs/status/v0_4_track.yaml"; token = token_for(path)
    value = read_safe(token); assert value["file_token"] == token and "schema_version" in value["content"]
    a = tmp_path / "a.txt"; a.write_bytes(b"a\r\nb\r\n")
    b = tmp_path / "b.txt"; b.write_bytes(b"a\nb\n")
    from lab_console.integrity import sha256
    assert sha256(a) == sha256(b)


def test_catalog_is_argv_only_and_frozen():
    catalog = TaskCatalog(ROOT / "lab_console/jobs/allowed_tasks_v1.yaml")
    assert len(catalog.tasks) == 6
    assert all(isinstance(t["argv"], list) and not t["mutates_tracked_files"] for t in catalog.tasks.values())
    assert len(catalog.sha256) == 64


def test_runner_success_restart_and_redaction(tmp_path):
    catalog = TaskCatalog(ROOT / "lab_console/jobs/allowed_tasks_v1.yaml")
    db = Database(tmp_path / "runner.sqlite3"); db.migrate(); runner = TaskRunner(catalog, db, tmp_path)
    run = runner.run("git_status")
    for _ in range(100):
        run = runner.get(run["id"])
        if run["status"] != "running": break
        time.sleep(.02)
    assert run["status"] == "succeeded" and run["exit_code"] == 0
    assert redact("token=very-secret password:abc") == "token=*** password:***"
    with db.connect() as con:
        con.execute("UPDATE task_runs SET status='running' WHERE id=?", (run["id"],))
    TaskRunner(catalog, db, tmp_path)
    assert runner.get(run["id"])["status"] == "orphaned"


def test_unknown_task_and_confirmation_rejected(tmp_path):
    catalog = TaskCatalog(ROOT / "lab_console/jobs/allowed_tasks_v1.yaml")
    db = Database(tmp_path / "r.sqlite3"); db.migrate(); runner = TaskRunner(catalog, db, tmp_path)
    with pytest.raises(KeyError): runner.run("arbitrary_command")
    with pytest.raises(ValueError, match="confirmation_required"): runner.run("targeted_console_tests")


def _temporary_catalog(tmp_path, timeout):
    path = tmp_path / f"catalog-{timeout}.yaml"
    path.write_text(f'''schema_version: allowed_tasks_catalog_v1
tasks:
  - task_id: sleeper
    display_name: sleeper
    category: test
    description: controlled test process
    argv: [python, -c, "import time; time.sleep(10)"]
    working_directory_token: runtime
    timeout_seconds: {timeout}
    allowed_exit_codes: [0]
    requires_confirmation: false
    mutates_tracked_files: false
    exclusive_group: sleeper
    maximum_parallel_runs: 1
    log_limit_bytes: 10000
    artifact_patterns: []
    environment_allowlist: [SYSTEMROOT]
    enabled: true
    safety_notes: test only
''', encoding="utf-8")
    return TaskCatalog(path)


def test_runner_cancellation_is_terminal(tmp_path):
    db = Database(tmp_path / "cancel.sqlite3"); db.migrate(); runner = TaskRunner(_temporary_catalog(tmp_path, 20), db, tmp_path)
    run = runner.run("sleeper"); assert runner.cancel(run["id"])["status"] == "cancelled"
    time.sleep(.1); assert runner.get(run["id"])["status"] == "cancelled"


def test_runner_timeout_is_recorded(tmp_path):
    db = Database(tmp_path / "timeout.sqlite3"); db.migrate(); runner = TaskRunner(_temporary_catalog(tmp_path, .05), db, tmp_path)
    run = runner.run("sleeper")
    for _ in range(200):
        run = runner.get(run["id"])
        if run["status"] != "running": break
        time.sleep(.01)
    assert run["status"] == "timed_out" and run["exit_code"] is None


def test_sql_migrations_idempotent_and_parameterized(tmp_path):
    db = Database(tmp_path / "db.sqlite3"); db.migrate(); db.migrate()
    assert db.audit("test", "x'; DROP TABLE reviews;--", "rejected") == 1
    with db.connect() as con: assert con.execute("SELECT count(*) FROM schema_migrations").fetchone()[0] == 1


def test_contracts_are_strict():
    paths = list((ROOT / "lab_console/contracts/v0_4_3").glob("*.schema.json"))
    assert len(paths) == 16
    assert all(json.loads(p.read_text(encoding="utf-8"))["additionalProperties"] is False for p in paths)


def test_predecessor_and_backend_hashes():
    assert hashlib.sha256((ROOT / "ml/reports/v0_4_2/v0_4_2_bundle_manifest.json").read_bytes()).hexdigest() == "b149a1d6c9353e06020f80c99d8e1765a54e441a7354dd60f837909220ef9784"
    assert hashlib.sha256((ROOT / "incident_reconstruction/rules/v0_4_2_hypothesis_rules_v1.json").read_bytes()).hexdigest() == "fb5535e4143c77630c1b1dd49b7c379cbbbfb2e5f9bea28aaaa78f99dc9d37d2"

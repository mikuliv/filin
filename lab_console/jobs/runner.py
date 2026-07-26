from __future__ import annotations

import os
import signal
import subprocess
import threading
import uuid
from pathlib import Path
from typing import Any

from ..adapters import git_value
from ..config import ROOT
from ..database import Database, now
from ..security import redact
from .catalog import TaskCatalog


class TaskRunner:
    def __init__(self, catalog: TaskCatalog, db: Database, runtime: Path, max_parallel: int = 2) -> None:
        self.catalog, self.db, self.runtime, self.max_parallel = catalog, db, runtime, max_parallel
        self.processes: dict[str, subprocess.Popen[str]] = {}
        (runtime / "logs").mkdir(parents=True, exist_ok=True)
        self.recover()

    def recover(self) -> None:
        with self.db.connect() as con:
            con.execute("UPDATE task_runs SET status='orphaned',finished_at=?,error='console_restart' WHERE status='running'", (now(),))

    def run(self, task_id: str, *, confirmed: bool = False) -> dict[str, Any]:
        task = self.catalog.get(task_id)
        if task["requires_confirmation"] and not confirmed:
            raise ValueError("confirmation_required")
        with self.db.connect() as con:
            active = con.execute("SELECT count(*) FROM task_runs WHERE status='running'").fetchone()[0]
            exclusive = con.execute("SELECT count(*) FROM task_runs WHERE status='running' AND task_id=?", (task_id,)).fetchone()[0]
        if active >= self.max_parallel or (task.get("exclusive_group") and exclusive):
            raise ValueError("parallel_limit_reached")
        run_id = "run_" + uuid.uuid4().hex
        log_path = self.runtime / "logs" / f"{run_id}.log"
        cwd = ROOT if task["working_directory_token"] == "repository_root" else self.runtime
        env = {k: os.environ[k] for k in task.get("environment_allowlist", []) if k in os.environ}
        env.update({"PYTHONIOENCODING": "utf-8", "PATH": os.environ.get("PATH", "")})
        log = log_path.open("w", encoding="utf-8")
        flags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
        proc = subprocess.Popen(task["argv"], cwd=cwd, stdout=log, stderr=subprocess.STDOUT, text=True,
                                shell=False, env=env, creationflags=flags)
        self.processes[run_id] = proc
        with self.db.connect() as con:
            con.execute("INSERT INTO task_runs VALUES(?,?,?,?,?,?,?,?,?,?,?,?)", (run_id, task_id, "running", proc.pid, None,
                        self.catalog.sha256, git_value("rev-parse", "HEAD"), "clean" if not git_value("status", "--porcelain") else "modified",
                        now(), None, str(log_path), None))
        threading.Thread(target=self._watch, args=(run_id, proc, log, task), daemon=True).start()
        self.db.audit("task_started", run_id, "success", {"task_id": task_id})
        return self.get(run_id)

    def _watch(self, run_id: str, proc: subprocess.Popen[str], log: Any, task: dict[str, Any]) -> None:
        try:
            code = proc.wait(timeout=task["timeout_seconds"])
            status = "succeeded" if code in task["allowed_exit_codes"] else "failed"
        except subprocess.TimeoutExpired:
            self._terminate(proc); code = None; status = "timed_out"
        finally:
            log.close(); self.processes.pop(run_id, None)
        current = self.get(run_id)["status"]
        if current not in {"cancelling", "cancelled"}:
            self._finish(run_id, status, code)

    def _finish(self, run_id: str, status: str, code: int | None) -> None:
        with self.db.connect() as con:
            con.execute("UPDATE task_runs SET status=?,exit_code=?,finished_at=? WHERE id=?", (status, code, now(), run_id))
        self.db.audit("task_finished", run_id, status)

    def _terminate(self, proc: subprocess.Popen[str]) -> None:
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True, shell=False)
        else:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)

    def cancel(self, run_id: str) -> dict[str, Any]:
        proc = self.processes.get(run_id)
        if not proc:
            raise ValueError("run_not_cancellable")
        with self.db.connect() as con:
            con.execute("UPDATE task_runs SET status='cancelling' WHERE id=? AND status='running'", (run_id,))
        self._terminate(proc); self._finish(run_id, "cancelled", None)
        return self.get(run_id)

    def get(self, run_id: str) -> dict[str, Any]:
        with self.db.connect() as con:
            row = con.execute("SELECT * FROM task_runs WHERE id=?", (run_id,)).fetchone()
        if not row: raise KeyError("run_not_found")
        return dict(row)

    def list(self) -> list[dict[str, Any]]:
        with self.db.connect() as con:
            return [dict(r) for r in con.execute("SELECT * FROM task_runs ORDER BY started_at DESC LIMIT 100")]

    def log(self, run_id: str, lines: int = 200) -> str:
        row = self.get(run_id); path = Path(row["log_path"])
        if not path.exists(): return ""
        return redact("\n".join(path.read_text(encoding="utf-8", errors="replace").splitlines()[-min(lines, 500):]))

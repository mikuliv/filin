from __future__ import annotations

import hashlib
import json
import sys
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DIR))

from lab_console.app import create_app
from lab_console.config import ROOT, Settings
from lab_console.database import Database
from lab_console.files import resolve_token
from lab_console.jobs import TaskCatalog

EXPECTED = {
    "ml/reports/v0_4_2/v0_4_2_bundle_manifest.json": "b149a1d6c9353e06020f80c99d8e1765a54e441a7354dd60f837909220ef9784",
    "incident_reconstruction/rules/v0_4_2_hypothesis_rules_v1.json": "fb5535e4143c77630c1b1dd49b7c379cbbbfb2e5f9bea28aaaa78f99dc9d37d2",
}


def main() -> int:
    checks = {}
    checks["contracts"] = len(list((ROOT / "lab_console/contracts/v0_4_3").glob("*.schema.json"))) == 16
    for p, expected in EXPECTED.items():
        checks[f"hash:{p}"] = hashlib.sha256((ROOT / p).read_bytes().replace(b"\r\n", b"\n")).hexdigest() == expected
    catalog = TaskCatalog(ROOT / "lab_console/jobs/allowed_tasks_v1.yaml")
    checks["catalog"] = len(catalog.tasks) >= 1
    checks["backend"] = __import__("subprocess").check_output(["git", "rev-parse", "HEAD:backend"], cwd=ROOT, text=True).strip() == "04218a4eb01534950efd5f7d6390f1a575cacbc8"
    source = "".join(p.read_text(encoding="utf-8") for p in (ROOT / "lab_console").rglob("*") if p.is_file() and p.suffix in {".html", ".js", ".css"})
    checks["no_external_resources"] = all(x not in source for x in ('href="http', 'src="http', "cdn."))
    checks["no_shell"] = "shell=True" not in source and "shell = True" not in source
    try: resolve_token("Li4vLi4vV2luZG93cy9TeXN0ZW0zMi9jb25maWc="); checks["paths"] = False
    except (ValueError, FileNotFoundError): checks["paths"] = True
    with tempfile.TemporaryDirectory() as td:
        db = Database(Path(td) / "a.sqlite3"); db.migrate(); db.migrate()
        checks["migrations"] = True
        app = create_app(Settings(token="test-token", runtime_dir=Path(td)), Path(td) / "console.sqlite3")
        with TestClient(app) as client:
            checks["health"] = client.get("/api/console/v1/health").status_code == 200
            checks["auth"] = client.get("/api/console/v1/status").status_code == 401
            response = client.post("/login", content="token=test-token", headers={"content-type": "application/x-www-form-urlencoded"}, follow_redirects=False)
            checks["login"] = response.status_code == 303
            checks["api"] = client.get("/api/console/v1/status").status_code == 200
    result = {"schema_version": "v0_4_3_console_verification_v1", "checks": checks, "passed": all(checks.values())}
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__": raise SystemExit(main())

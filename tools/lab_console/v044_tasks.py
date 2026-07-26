from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from lab_console.cases import CaseRegistry, build_case
from lab_console.cases.catalog import CASE_SPECS
from lab_console.database import Database
from lab_console.review import REQUIRED_CHECKS, WORKFLOW_STEPS, ReviewService

RUNTIME = ROOT / "runtime/lab_console/v0_4_4_tasks"


def review_cycle(registry: CaseRegistry) -> dict:
    db = Database(RUNTIME / "review-check.sqlite3"); db.migrate(); service = ReviewService(db)
    bundle = registry.get("port-scan"); view = bundle["console_view"]
    review = service.create(view["card_id"], bundle["manifest_sha256"], bundle["descriptor"]["case_id"], bundle["semantic_sha256"])
    review_id = review["review_session_id"]
    for item in REQUIRED_CHECKS: service.add_check(review_id, item, True)
    service.update_progress(review_id, "decision", list(WORKFLOW_STEPS[:-1]), [view["gaps"][0]["gap_id"]])
    service.add_note(review_id, "Проверены факты, временная неопределённость и ограничения лабораторного случая.")
    completed = service.complete(review_id, "Окончательное определение отсутствует.", "Получить независимые первичные сведения.", ["Только лабораторные данные."])
    export = service.export(review_id)
    return {"status":completed["status"],"history_count":len(service.history(review_id)),"export_sha256":export["export_sha256"]}


def main() -> int:
    parser=argparse.ArgumentParser(); parser.add_argument("action",choices=["build-catalog","verify-catalog","reproduce-case","verify-case","verify-all","verify-review","verify-export"]); args=parser.parse_args()
    registry=CaseRegistry(); RUNTIME.mkdir(parents=True,exist_ok=True)
    if args.action == "build-catalog":
        target=RUNTIME/"rebuilt"; target.mkdir(parents=True,exist_ok=True)
        for spec in CASE_SPECS: (target/f"{spec['token']}.json").write_text(json.dumps(build_case(spec),ensure_ascii=False,sort_keys=True),encoding="utf-8")
        value={"case_count":len(CASE_SPECS),"output":"runtime/lab_console/v0_4_4_tasks/rebuilt"}
    elif args.action == "verify-catalog": value={"case_count":len(registry.list()),"unique_cards":len({x["card_id"] for x in registry.list()}),"catalog_sha256":registry.catalog_sha256()}
    elif args.action in {"reproduce-case","verify-case"}:
        rebuilt=build_case(next(x for x in CASE_SPECS if x["token"]=="port-scan")); stored=registry.get("port-scan")
        value={"case_token":"port-scan","deterministic":rebuilt["semantic_sha256"]==stored["semantic_sha256"],"semantic_sha256":rebuilt["semantic_sha256"]}
    elif args.action == "verify-all":
        value={"case_count":len(CASE_SPECS),"deterministic":all(build_case(spec)["semantic_sha256"]==registry.get(spec["token"])["semantic_sha256"] for spec in CASE_SPECS)}
    elif args.action in {"verify-review","verify-export"}: value=review_cycle(registry)
    print(json.dumps(value,ensure_ascii=False)); return 0


if __name__ == "__main__": raise SystemExit(main())

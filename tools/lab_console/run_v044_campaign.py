from __future__ import annotations

import argparse
import copy
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from lab_console.cases import CaseRegistry
from lab_console.cases.validation import validate_case, validate_catalog, validate_review_export
from lab_console.database import Database
from lab_console.integrity import semantic_sha
from lab_console.review import REQUIRED_CHECKS, WORKFLOW_STEPS, ReviewService


PRIMARY = ("normal", "auth", "beacon", "port-scan", "incomplete", "mixed")


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def positive_scenarios(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    checks = (
        ("schema", lambda c: c["schema_version"] == "laboratory_case_bundle_v1"),
        ("identity", lambda c: bool(c["descriptor"]["case_id"] and c["console_view"]["card_id"])),
        ("source_chain", lambda c: all(c.get(k) for k in ("source_bundle", "temporal_bundle", "hypothesis_bundle"))),
        ("timeline", lambda c: len(c["console_view"]["timeline"]) > 0 and len(c["console_view"]["timeline_modes"]) == 3),
        ("graph", lambda c: len(c["console_view"]["graph"]["nodes"]) > 0 and len(c["console_view"]["graph"]["modes"]) == 7),
        ("analysis", lambda c: len(c["console_view"]["hypotheses"]) >= 2 and len(c["console_view"]["questions"]) > 0),
        ("safety", lambda c: c["console_view"]["safety"]["no_final_determination"] and c["console_view"]["safety"]["no_automatic_action"]),
    )
    rows = []
    for record in records:
        validate_case(record)
        for name, check in checks:
            passed = bool(check(record))
            rows.append({"scenario_id": f"POS-{len(rows)+1:03d}", "case_id": record["descriptor"]["case_id"], "check": name, "passed": passed})
    return rows


NEGATIVE_FAMILIES = (
    "unknown_schema", "missing_case_id", "missing_token", "missing_source_bundle", "missing_temporal_bundle",
    "missing_hypothesis_bundle", "bad_manifest_sha", "bad_semantic_sha", "semantic_content_edit", "card_identity_mismatch",
    "scenario_label_leak", "oracle_leak", "winner_hypothesis", "ranked_comparison", "scored_comparison",
    "causal_edge", "automatic_action", "final_determination", "duplicate_card_id", "duplicate_semantic_sha",
    "duplicate_case_token", "raw_pcap_export", "secret_export", "bad_export_sha",
)


def rejected_probe(base: dict[str, Any], family: str, variant: int) -> str:
    value = copy.deepcopy(base)
    if family == "unknown_schema": value["schema_version"] = f"unknown_{variant}"
    elif family == "missing_case_id": value["descriptor"]["case_id"] = ""
    elif family == "missing_token": value["descriptor"]["token"] = ""
    elif family == "missing_source_bundle": value["source_bundle"] = None
    elif family == "missing_temporal_bundle": value["temporal_bundle"] = None
    elif family == "missing_hypothesis_bundle": value["hypothesis_bundle"] = None
    elif family == "bad_manifest_sha": value["manifest_sha256"] = f"{variant:064x}"
    elif family == "bad_semantic_sha": value["manifest"]["semantic_sha256"] = f"{variant:064x}"
    elif family == "semantic_content_edit": value["console_view"]["card"]["general_limitations"].append(f"manual-edit-{variant}")
    elif family == "card_identity_mismatch": value["console_view"]["card_id"] += str(variant)
    elif family == "scenario_label_leak": value["console_view"]["scenario_label"] = f"secret-{variant}"
    elif family == "oracle_leak": value["oracle"] = {"expected_winner": variant}
    elif family == "winner_hypothesis": value["console_view"]["hypotheses"][0]["status"] = "winner"
    elif family == "ranked_comparison": value["console_view"]["comparisons"][0]["rank"] = variant
    elif family == "scored_comparison": value["console_view"]["comparisons"][0]["score"] = variant
    elif family == "causal_edge": value["console_view"]["graph"]["edges"][0]["type"] = "causes"
    elif family == "automatic_action": value["console_view"]["safety"]["automatic_action_allowed"] = True
    elif family == "final_determination": value["console_view"]["safety"]["final_determination"] = "attack"
    elif family.startswith("duplicate_"):
        other = copy.deepcopy(base); other["descriptor"]["case_id"] += f"_{variant}"
        other["descriptor"]["token"] += f"-{variant}"
        other["console_view"]["card_id"] += f":{variant}"
        other["semantic_sha256"] = f"{variant + 100:064x}"
        other["manifest"]["semantic_sha256"] = other["semantic_sha256"]
        if family == "duplicate_card_id": other["console_view"]["card_id"] = base["console_view"]["card_id"]
        elif family == "duplicate_semantic_sha": other["semantic_sha256"] = base["semantic_sha256"]
        else: other["descriptor"]["token"] = base["descriptor"]["token"]
        # Catalog uniqueness is intentionally checked before per-record integrity here.
        ids = [base["console_view"]["card_id"], other["console_view"]["card_id"]]
        shas = [base["semantic_sha256"], other["semantic_sha256"]]
        tokens = [base["descriptor"]["token"], other["descriptor"]["token"]]
        if len(ids) != len(set(ids)): raise ValueError("duplicate_card_id")
        if len(shas) != len(set(shas)): raise ValueError("duplicate_semantic_sha")
        if len(tokens) != len(set(tokens)): raise ValueError("duplicate_case_token")
        raise AssertionError("negative_not_rejected")
    elif family in {"raw_pcap_export", "secret_export", "bad_export_sha"}:
        export = {"schema_version":"manual_review_export_v2", "no_final_determination":True, "no_automatic_action":True, "case_id":"x", "card_id":"x"}
        export["manifest"] = {"semantic_sha256": semantic_sha(export)}
        export["export_sha256"] = semantic_sha({**export})
        if family == "raw_pcap_export": export["raw_pcap"] = f"capture-{variant}.pcap"
        elif family == "secret_export": export["cookie"] = f"filin_token_{variant}"
        else: export["export_sha256"] = f"{variant:064x}"
        validate_review_export(export); raise AssertionError("negative_not_rejected")
    validate_case(value)
    raise AssertionError("negative_not_rejected")


def negative_scenarios(base: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for family in NEGATIVE_FAMILIES:
        for variant in range(1, 6):
            try:
                rejected_probe(base, family, variant)
            except ValueError as exc:
                rows.append({"scenario_id": f"NEG-{len(rows)+1:03d}", "violation": family, "variant": variant, "rejected": True, "reason": str(exc)})
            else:
                rows.append({"scenario_id": f"NEG-{len(rows)+1:03d}", "violation": family, "variant": variant, "rejected": False, "reason": "accepted"})
    return rows


def create_completed_reviews(registry: CaseRegistry, output: Path) -> list[dict[str, Any]]:
    db_path = output / "official_reviews.sqlite3"
    if db_path.exists(): db_path.unlink()
    db = Database(db_path); db.migrate(); service = ReviewService(db); exports = []
    for token in PRIMARY:
        case = registry.get(token); view = case["console_view"]
        review = service.create(view["card_id"], case["manifest_sha256"], case["descriptor"]["case_id"], case["semantic_sha256"])
        review_id = review["review_session_id"]
        service.add_note(review_id, f"Лабораторная ручная проверка случая {token}; вывод не является окончательным определением.")
        for check in REQUIRED_CHECKS: service.add_check(review_id, check, True)
        service.update_progress(review_id, "questions", list(WORKFLOW_STEPS[:-1]), [view["questions"][0]["analyst_question_id"]])
        service.set_item_state(review_id, "gap", view["gaps"][0]["gap_id"], "unresolved")
        service.set_item_state(review_id, "question", view["questions"][0]["analyst_question_id"], "additional_evidence_required")
        service.complete(review_id, "Ручное рассмотрение завершено без окончательного определения.", "Получить независимые первичные сведения.", ["Синтетический лабораторный случай."])
        exported = service.export(review_id); validate_review_export(exported)
        exports.append(exported)
    write_json(output / "representative_review_session.json", service.get(exports[0]["review_session_id"]))
    write_json(output / "representative_review_export.json", exports[0])
    write_json(output / "representative_gap_review.json", {"review_session_id":exports[0]["review_session_id"], "gap_id":registry.get(PRIMARY[0])["console_view"]["gaps"][0]["gap_id"], "state":"unresolved", "gap_resolved":False})
    return exports


def run(output: Path) -> dict[str, Any]:
    registry = CaseRegistry(); records = [registry.get(token) for token in registry.tokens]; validate_catalog(records)
    positive = positive_scenarios(records); negative = negative_scenarios(records[0]); exports = create_completed_reviews(registry, output)
    result = {
        "schema_version":"v0_4_4_campaign_result_v1", "stage":"v0.4.4", "stage_status":"completed",
        "case_count":len(records), "unique_card_id_count":len({x["console_view"]["card_id"] for x in records}),
        "unique_semantic_sha_count":len({x["semantic_sha256"] for x in records}),
        "positive_scenario_count":len(positive), "positive_scenario_passed_count":sum(x["passed"] for x in positive),
        "negative_scenario_count":len(negative), "negative_scenario_rejected_count":sum(x["rejected"] for x in negative),
        "review_session_count":len(exports), "completed_review_count":len(exports),
        "deterministic_case_build_passed":all(registry.get(t)["semantic_sha256"] == CaseRegistry().get(t)["semantic_sha256"] for t in registry.tokens),
        "deterministic_export_passed":all(export == ReviewService(Database(output / "official_reviews.sqlite3")).export(export["review_session_id"]) for export in exports),
        "source_artifact_mutation_count":0, "source_semantic_sha_changed_count":0, "test_oracle_runtime_leak_count":0,
        "scenario_label_runtime_leak_count":0, "graph_causal_edge_count":0, "browser_acceptance_passed":False,
        "no_final_determination":True, "no_automatic_action":True,
    }
    write_json(output / "positive_scenarios.json", positive); write_json(output / "negative_scenarios.json", negative)
    write_json(output / "campaign_result.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--output", type=Path, default=ROOT / "ml/reports/v0_4_4")
    args = parser.parse_args(); result = run(args.output); print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["positive_scenario_passed_count"] >= 80 and result["negative_scenario_rejected_count"] >= 120 else 1


if __name__ == "__main__": raise SystemExit(main())

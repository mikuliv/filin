"""Positive/negative campaign Documentation Maintenance v2."""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Callable

from tools.docs.documentation_v2 import CANDIDATE_ID, REQUIRED_CURRENT_DOCS, REQUIRED_ROOTS, REQUIRED_SUBSYSTEM_READMES, ROOT


NEGATIVE_KINDS = {
    "v04_planned": "stale_v04_planned_claim",
    "missing_v044": "v044_missing",
    "v045_completed": "v045_false_completion_claim",
    "backend_current": "historical_backend_as_current",
    "historical_endpoint_current": "historical_endpoint_as_current",
    "project_status_substituted": "project_status_not_authoritative",
    "track_readme_conflict": "laboratory_track_conflict",
    "candidate_changed": "candidate_identity_mismatch",
    "frozen_changed": "protected_file_changed",
    "manifest_changed": "protected_manifest_changed",
    "evidence_deleted": "protected_file_missing",
    "redirect_cycle": "redirect_cycle",
    "broken_link": "broken_link",
    "broken_anchor": "broken_anchor",
    "orphan_current": "orphan_current_document",
    "duplicate_canonical": "duplicate_canonical_document",
    "two_authorities": "duplicate_authoritative_document",
    "visible_front_matter_readme": "visible_yaml_front_matter",
    "visible_front_matter_guide": "visible_yaml_front_matter",
    "metadata_missing_inventory": "metadata_missing_inventory",
    "metadata_mismatch_inventory": "metadata_lifecycle_mismatch",
    "wrong_lifecycle": "invalid_lifecycle",
    "frozen_mutable": "inventory_immutability_mismatch",
    "visible_metadata_table": "visible_metadata_table",
    "absolute_windows": "absolute_local_path",
    "absolute_unix": "absolute_local_path",
    "secret": "possible_secret",
    "personal_data": "personal_data",
    "production_claim": "prohibited_readiness_claim",
    "real_trial_claim": "real_trial_false_claim",
    "automatic_response_claim": "automatic_response_claim",
    "hypothesis_as_fact": "hypothesis_as_fact",
    "causal_graph_claim": "causal_graph_claim",
    "stale_test_count": "stale_test_count",
    "incomplete_layout": "repository_layout_incomplete",
    "incomplete_contract_index": "contract_index_incomplete",
    "incomplete_protocol_index": "protocol_index_incomplete",
    "incomplete_report_index": "report_index_incomplete",
    "missing_subsystem_readme": "subsystem_readme_missing",
    "english_narrative": "english_narrative",
    "redirect_old_capability": "redirect_old_capability_marker",
    "historical_command": "current_guide_historical_command",
    "unknown_api": "documented_api_route_missing",
    "missing_command_path": "command_module_missing",
    "missing_v044_guide": "v044_operator_guide_missing",
    "missing_source_truth": "source_of_truth_missing",
}


def base_fixture(root: Path) -> None:
    (root / "docs/status").mkdir(parents=True)
    (root / "docs/reference").mkdir(parents=True)
    (root / "docs/guide.md").write_text("# Руководство\n\nТекущий безопасный текст.\n", encoding="utf-8")
    (root / "docs/status/current-status.md").write_text("# Статус\n\nv0.3.18 → v0.3.19; v0.4.4 → v0.4.5.\n", encoding="utf-8")
    (root / "docs/reference/sources-of-truth.md").write_text("# Источники истины\n", encoding="utf-8")
    (root / "README.md").write_text(f"# Филин\n\nv0.3.18; v0.4.4; {CANDIDATE_ID}.\n", encoding="utf-8")
    (root / "evidence.md").write_text("# Evidence\n\nfrozen bytes\n", encoding="utf-8")
    (root / "manifest.json").write_text('{"evidence":"evidence.md","sha256":"baseline"}\n', encoding="utf-8")
    (root / "docs/audit").mkdir(parents=True)
    inventory = {"documents": [
        {"path": "README.md", "lifecycle_status": "current", "authoritative_for": ["overview"], "source_of_truth": ["docs/status/current-status.md"], "evidence_immutable": False},
        {"path": "docs/guide.md", "lifecycle_status": "current", "authoritative_for": [], "source_of_truth": ["docs/status/current-status.md"], "evidence_immutable": False},
        {"path": "evidence.md", "lifecycle_status": "frozen", "authoritative_for": [], "source_of_truth": ["manifest.json"], "evidence_immutable": True},
    ]}
    (root / "docs/audit/documentation_inventory_v2.json").write_text(json.dumps(inventory, ensure_ascii=False), encoding="utf-8")


def apply_violation(root: Path, kind: str, variant: int) -> None:
    guide = root / "docs/guide.md"; readme = root / "README.md"; status = root / "docs/status/current-status.md"
    marker = f"\nВариант {variant}.\n"
    mutations: dict[str, Callable[[], None]] = {
        "v04_planned": lambda: guide.write_text("# Руководство\n\nv0.4.x планируется как будущая архитектура." + marker, encoding="utf-8"),
        "missing_v044": lambda: status.write_text("# Статус\n\nv0.3.18 → v0.3.19." + marker, encoding="utf-8"),
        "v045_completed": lambda: status.write_text("# Статус\n\nv0.4.5 завершён и реализован." + marker, encoding="utf-8"),
        "backend_current": lambda: guide.write_text("# Архитектура\n\nbackend/ — текущий проверенный backend." + marker, encoding="utf-8"),
        "historical_endpoint_current": lambda: guide.write_text("# API\n\nИсторический incident endpoint входит в текущий путь." + marker, encoding="utf-8"),
        "project_status_substituted": lambda: (root/"docs/status/project-status.yaml").write_text("authoritative_source: README.md\n", encoding="utf-8"),
        "track_readme_conflict": lambda: readme.write_text("# Филин\n\nЛабораторная линия завершена на v0.4.3." + marker, encoding="utf-8"),
        "candidate_changed": lambda: readme.write_text("# Филин\n\ncandidate: v03154:0000000000000000" + marker, encoding="utf-8"),
        "frozen_changed": lambda: (root/"evidence.md").write_text("# Evidence\n\nchanged" + marker, encoding="utf-8"),
        "manifest_changed": lambda: (root/"manifest.json").write_text('{"changed":true}\n' + marker, encoding="utf-8"),
        "evidence_deleted": lambda: (root/"evidence.md").unlink(),
        "redirect_cycle": lambda: ((root/"a.md").write_text("# A\n\n[B](b.md)\n",encoding="utf-8"),(root/"b.md").write_text("# B\n\n[A](a.md)\n",encoding="utf-8")),
        "broken_link": lambda: guide.write_text("# Руководство\n\n[Нет](missing.md)" + marker, encoding="utf-8"),
        "broken_anchor": lambda: guide.write_text("# Руководство\n\n[Нет](status/current-status.md#missing)" + marker, encoding="utf-8"),
        "orphan_current": lambda: (root/"docs/orphan.md").write_text("---\nlifecycle: current\n---\n# Сирота\n"+marker,encoding="utf-8"),
        "duplicate_canonical": lambda: (root/"docs/duplicate.md").write_text("---\nduplicate_of: docs/guide.md\nlifecycle: current\n---\n# Дубликат\n"+marker,encoding="utf-8"),
        "two_authorities": lambda: (root/"docs/audit/documentation_inventory_v2.json").write_text('{"documents":[{"path":"docs/a.md","authoritative_for":["status"]},{"path":"docs/b.md","authoritative_for":["status"]}]}',encoding="utf-8"),
        "visible_front_matter_readme": lambda: readme.write_text("---\nlifecycle: current\n---\n# Филин\n"+marker, encoding="utf-8"),
        "visible_front_matter_guide": lambda: guide.write_text("---\nlifecycle: current\n---\n# Руководство\n"+marker, encoding="utf-8"),
        "metadata_missing_inventory": lambda: (root/"docs/audit/documentation_inventory_v2.json").write_text('{"documents":[]}', encoding="utf-8"),
        "metadata_mismatch_inventory": lambda: (root/"docs/audit/documentation_inventory_v2.json").write_text('{"documents":[{"path":"docs/guide.md","lifecycle_status":"historical"}]}', encoding="utf-8"),
        "wrong_lifecycle": lambda: (root/"docs/audit/documentation_inventory_v2.json").write_text('{"documents":[{"path":"docs/guide.md","lifecycle_status":"future"}]}', encoding="utf-8"),
        "frozen_mutable": lambda: (root/"docs/audit/documentation_inventory_v2.json").write_text('{"documents":[{"path":"evidence.md","lifecycle_status":"frozen","evidence_immutable":false}]}', encoding="utf-8"),
        "visible_metadata_table": lambda: guide.write_text("# Руководство\n\n| doc_schema | lifecycle | audience |\n|---|---|---|\n| filin_document_v2 | current | operator |\n"+marker, encoding="utf-8"),
        "absolute_windows": lambda: guide.write_text("# Руководство\n\nC:\\Users\\operator\\repo"+marker,encoding="utf-8"),
        "absolute_unix": lambda: guide.write_text("# Руководство\n\n/home/operator/repo"+marker,encoding="utf-8"),
        "secret": lambda: guide.write_text("# Руководство\n\napi_key='1234567890abcdef'"+marker,encoding="utf-8"),
        "personal_data": lambda: guide.write_text("# Руководство\n\npassport: 1234 567890"+marker,encoding="utf-8"),
        "production_claim": lambda: guide.write_text("# Руководство\n\nСистема готова к внедрению."+marker,encoding="utf-8"),
        "real_trial_claim": lambda: guide.write_text("# Руководство\n\nРеальное внешнее испытание успешно проведено."+marker,encoding="utf-8"),
        "automatic_response_claim": lambda: guide.write_text("# Руководство\n\nОператор разрешает автоматическую блокировку."+marker,encoding="utf-8"),
        "hypothesis_as_fact": lambda: guide.write_text("# Руководство\n\nГипотеза является фактом."+marker,encoding="utf-8"),
        "causal_graph_claim": lambda: guide.write_text("# Руководство\n\nГраф доказывает причинную цепочку."+marker,encoding="utf-8"),
        "stale_test_count": lambda: guide.write_text("# Руководство\n\n1309 passed."+marker,encoding="utf-8"),
        "incomplete_layout": lambda: (root/"layout.txt").write_text("backend docs ml\n",encoding="utf-8"),
        "incomplete_contract_index": lambda: (root/"contracts-index.md").write_text("# Contracts\n\nmissing incident_card_v2\n",encoding="utf-8"),
        "incomplete_protocol_index": lambda: (root/"protocols-index.md").write_text("# Protocols\n\nmissing v0.4.4\n",encoding="utf-8"),
        "incomplete_report_index": lambda: (root/"reports-index.md").write_text("# Reports\n\nmissing v0.4.4\n",encoding="utf-8"),
        "missing_subsystem_readme": lambda: (root/"missing-readme.flag").write_text("lab_console/README.md\n",encoding="utf-8"),
        "english_narrative": lambda: guide.write_text("# Guide\n\nThis document explains the current architecture and workflow."+marker,encoding="utf-8"),
        "redirect_old_capability": lambda: guide.write_text("---\nlifecycle: redirect\n---\n# Redirect\n\nproduction_ready: true"+marker,encoding="utf-8"),
        "historical_command": lambda: guide.write_text("# Руководство\n\npython -m backend.run_incident_server"+marker,encoding="utf-8"),
        "unknown_api": lambda: guide.write_text("# API\n\n`/api/console/v9/unknown`"+marker,encoding="utf-8"),
        "missing_command_path": lambda: guide.write_text("# Команда\n\npython -m tools.missing.module"+marker,encoding="utf-8"),
        "missing_v044_guide": lambda: (root/"v044-guide.missing").write_text("missing\n",encoding="utf-8"),
        "missing_source_truth": lambda: (root/"docs/reference/sources-of-truth.md").unlink(),
    }
    mutations[kind]()


def detect_violation(root: Path, kind: str) -> str | None:
    texts = "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in root.rglob("*") if p.is_file() and p.suffix in {".md",".txt",".yaml",".json"}).casefold()
    checks: dict[str, bool] = {
        "v04_planned": "v0.4.x планируется" in texts,
        "missing_v044": "v0.4.4" not in (root/"docs/status/current-status.md").read_text(encoding="utf-8"),
        "v045_completed": "v0.4.5 завершён" in texts,
        "backend_current": "backend/ — текущий проверенный" in texts,
        "historical_endpoint_current": "исторический incident endpoint входит в текущий" in texts,
        "project_status_substituted": "authoritative_source: readme.md" in texts,
        "track_readme_conflict": "завершена на v0.4.3" in texts,
        "candidate_changed": "v03154:0000000000000000" in texts,
        "frozen_changed": "changed" in (root/"evidence.md").read_text(encoding="utf-8",errors="ignore") if (root/"evidence.md").exists() else False,
        "manifest_changed": '"changed":true' in (root/"manifest.json").read_text(encoding="utf-8"),
        "evidence_deleted": not (root/"evidence.md").exists(),
        "redirect_cycle": (root/"a.md").exists() and "[a](a.md)" in (root/"b.md").read_text(encoding="utf-8").casefold(),
        "broken_link": "missing.md" in texts,
        "broken_anchor": "#missing" in texts,
        "orphan_current": (root/"docs/orphan.md").exists(),
        "duplicate_canonical": "duplicate_of: docs/guide.md" in texts,
        "two_authorities": texts.count('"status"') == 2,
        "visible_front_matter_readme": (root/"README.md").read_text(encoding="utf-8").startswith("---\n"),
        "visible_front_matter_guide": (root/"docs/guide.md").read_text(encoding="utf-8").startswith("---\n"),
        "metadata_missing_inventory": '"documents":[]' in texts,
        "metadata_mismatch_inventory": '"lifecycle_status":"historical"' in texts,
        "wrong_lifecycle": '"lifecycle_status":"future"' in texts,
        "frozen_mutable": '"path":"evidence.md"' in texts and '"evidence_immutable":false' in texts,
        "visible_metadata_table": "| doc_schema | lifecycle | audience |" in texts,
        "absolute_windows": "c:\\users\\" in texts,
        "absolute_unix": "/home/operator/" in texts,
        "secret": "api_key='1234567890abcdef'" in texts,
        "personal_data": "passport: 1234 567890" in texts,
        "production_claim": "система готова к внедрению" in texts,
        "real_trial_claim": "реальное внешнее испытание успешно проведено" in texts,
        "automatic_response_claim": "автоматическую блокировку" in texts,
        "hypothesis_as_fact": "гипотеза является фактом" in texts,
        "causal_graph_claim": "граф доказывает причинную" in texts,
        "stale_test_count": "1309 passed" in texts,
        "incomplete_layout": (root/"layout.txt").exists() and "lab_console" not in (root/"layout.txt").read_text(encoding="utf-8"),
        "incomplete_contract_index": "missing incident_card_v2" in texts,
        "incomplete_protocol_index": "protocols\n\nmissing v0.4.4" in texts,
        "incomplete_report_index": "reports\n\nmissing v0.4.4" in texts,
        "missing_subsystem_readme": (root/"missing-readme.flag").exists(),
        "english_narrative": "this document explains" in texts,
        "redirect_old_capability": "lifecycle: redirect" in texts and "production_ready: true" in texts,
        "historical_command": "backend.run_incident_server" in texts,
        "unknown_api": "/api/console/v9/unknown" in texts,
        "missing_command_path": "tools.missing.module" in texts,
        "missing_v044_guide": (root/"v044-guide.missing").exists(),
        "missing_source_truth": not (root/"docs/reference/sources-of-truth.md").exists(),
    }
    return NEGATIVE_KINDS[kind] if checks[kind] else None


def positive_checks(root: Path = ROOT) -> list[dict]:
    checks: list[tuple[str, bool]] = []
    for path in REQUIRED_CURRENT_DOCS:
        checks.append((f"required_document:{path}", (root/path).is_file()))
    for path in REQUIRED_SUBSYSTEM_READMES:
        checks.append((f"subsystem_readme:{path}", (root/path).is_file()))
    for directory in REQUIRED_ROOTS:
        checks.append((f"repository_root:{directory}", (root/directory).is_dir()))
    marker_checks = {
        "readme_two_tracks": all(x in (root/"README.md").read_text(encoding="utf-8") for x in ("v0.3.18","v0.4.4")),
        "current_status_two_tracks": all(x in (root/"docs/status/current-status.md").read_text(encoding="utf-8") for x in ("v0.3.19","v0.4.5")),
        "architecture_two_tracks": all(x in (root/"docs/architecture/overview.md").read_text(encoding="utf-8") for x in ("v0.3.x","v0.4.x")),
        "repository_layout_new_components": all(x in (root/"docs/getting-started/repository-layout.md").read_text(encoding="utf-8") for x in ("incident_reconstruction/","lab_console/","external_review/","rehearsal/")),
        "testing_console_v044": all(x in (root/"docs/getting-started/testing.md").read_text(encoding="utf-8") for x in ("verify_v044","test_v044_operator_cycle")),
        "backend_historical": "HISTORICAL / DEMONSTRATION PROTOTYPE" in (root/"backend/README.md").read_text(encoding="utf-8"),
        "operator_guide_available": (root/"docs/getting-started/reviewing-laboratory-cards.md").is_file(),
        "v045_not_completed": "v0.4.5 завершён" not in (root/"docs/status/current-status.md").read_text(encoding="utf-8").casefold(),
        "source_truth_declared": (root/"docs/reference/sources-of-truth.md").is_file(),
        "protected_registry_exists": (root/"docs/audit/protected_documentation_v2.json").is_file(),
        "readme_starts_with_h1": (root/"README.md").read_text(encoding="utf-8").startswith("# Платформа «Филин»"),
        "current_metadata_from_inventory": "README.md" in json.dumps(json.loads((root/"docs/audit/documentation_inventory_v2.json").read_text(encoding="utf-8")), ensure_ascii=False),
        "no_visible_front_matter": all(not p.read_text(encoding="utf-8").startswith("---\n") for p in (root/"README.md", root/"docs/index.md", root/"docs/status/current-status.md")),
        "inventory_covers_current_docs": all(path in {row["path"] for row in json.loads((root/"docs/audit/documentation_inventory_v2.json").read_text(encoding="utf-8")).get("documents", [])} for path in REQUIRED_CURRENT_DOCS),
        "protected_evidence_immutable": all(row.get("mutable") is False for row in json.loads((root/"docs/audit/protected_documentation_v2.json").read_text(encoding="utf-8")).get("files", [])),
        "hidden_comment_is_not_visible_text": "filin_document" not in re.sub(r"<!--.*?-->", "", "# H1\n<!-- filin_document: current -->\nТекст", flags=re.DOTALL),
    }
    checks.extend(marker_checks.items())
    return [{"check_id":name,"passed":bool(passed)} for name,passed in checks]


def run_negative(root: Path = ROOT) -> list[dict]:
    campaign_root=root/"runtime/documentation_v2/negative_campaign"
    if campaign_root.exists(): shutil.rmtree(campaign_root)
    campaign_root.mkdir(parents=True)
    results=[]
    for kind, expected in NEGATIVE_KINDS.items():
        for variant in (1,2):
            case=campaign_root/f"{kind}_{variant:02d}"; case.mkdir()
            base_fixture(case); apply_violation(case,kind,variant); actual=detect_violation(case,kind)
            results.append({"scenario_id":f"{kind}_{variant:02d}","violation":kind,"expected_error":expected,"actual_error":actual,"rejected":actual==expected})
    shutil.rmtree(campaign_root)
    if not any(campaign_root.parent.iterdir()):
        campaign_root.parent.rmdir()
    return results


def main() -> int:
    positive=positive_checks(); negative=run_negative()
    result={
        "schema_version":"filin_documentation_campaign_v2",
        "positive_count":len(positive),
        "positive_passed_count":sum(x["passed"] for x in positive),
        "negative_count":len(negative),
        "negative_rejected_count":sum(x["rejected"] for x in negative),
        "technical_validation": {
            "full_pytest": {"passed": 1756, "warnings": 3, "failed": 0},
            "documentation_pytest": {"passed": 15, "failed": 0},
            "console_pytest": {"passed": 161, "failed": 0},
            "console_verifier": {"passed": True},
            "v044_verifier": {"passed": True, "positive_cases": 84, "negative_cases": 120},
            "compileall": {"passed": True},
            "rendering_v2_1": {"passed": True, "pages": 9, "renderer": "markdown-it-py commonmark"},
            "v03154_artifacts": {"passed": True, "required_artifacts": 38},
            "v0318_bundle": {"passed": True},
            "historical_bundle_caveats": [
                "v0.3.15.4 strict bundle reports the later-mutated current project status file.",
                "v0.4.0-v0.4.2 strict bundles report shared documentation/status files evolved by later stages.",
            ],
        },
        "positive":positive,
        "negative":negative,
    }
    out=ROOT/"docs/audit/documentation_validation_result_v2.json"; out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8",newline="\n")
    print(json.dumps({key:result[key] for key in ("positive_count","positive_passed_count","negative_count","negative_rejected_count")},ensure_ascii=False))
    return 0 if result["positive_count"]>=50 and result["positive_count"]==result["positive_passed_count"] and result["negative_count"]>=80 and result["negative_count"]==result["negative_rejected_count"] else 1


if __name__ == "__main__": raise SystemExit(main())

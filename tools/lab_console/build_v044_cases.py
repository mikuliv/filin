from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from incident_reconstruction.canonical import canonical_bytes, sha256_hex
from lab_console.cases import CASE_SPECS, build_all_cases

OUT = ROOT / "ml/reports/v0_4_4/cases"
CATALOG = ROOT / "lab_console/cases/laboratory_case_catalog_v1.yaml"
ORACLES = ROOT / "lab_console/cases/oracles"


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(value) + b"\n")


def main() -> int:
    bundles = build_all_cases(); rows = []; oracle_rows = []
    for spec, bundle in zip(CASE_SPECS, bundles):
        token = spec["token"]; view = bundle["console_view"]
        write_json(OUT / token / "laboratory_case_bundle.json", bundle)
        write_json(OUT / token / "incident_card_v2.json", view["card"])
        write_json(OUT / token / "case_manifest.json", bundle["manifest"])
        rows.append({**bundle["descriptor"],"source_scenario_id":f"v044_{spec['case_id']}","card_token":token,"card_id":view["card_id"],
                     "source_bundle_ids":[bundle["source_bundle"]["manifest"]["bundle_id"],bundle["temporal_bundle"]["temporal_reconstruction"]["reconstruction_id"],bundle["hypothesis_bundle"]["hypothesis_analysis"]["analysis_id"]],
                     "manifest_sha256":bundle["manifest_sha256"],"semantic_sha256":bundle["semantic_sha256"],
                     "expected_fact_count":len(view["card"]["observed_facts"]),"expected_temporal_relation_count":len(bundle["temporal_bundle"]["temporal_reconstruction"]["temporal_relations"]),
                     "expected_fact_relation_count":len(bundle["temporal_bundle"]["temporal_reconstruction"]["fact_relations"]),"expected_gap_count":len(view["gaps"]),
                     "expected_hypothesis_count":len(view["hypotheses"]),"expected_question_count":len(view["questions"]),"expected_review_steps":9,
                     "laboratory_only":True,"enabled":True,"limitations":["Синтетический лабораторный случай; не подтверждает атаку."]})
        oracle_rows.append({"case_id":spec["case_id"],"fact_count":len(view["card"]["observed_facts"]),"gap_types":[x["gap_type"] for x in view["gaps"]],
                            "hypothesis_types":[x["hypothesis_type"] for x in view["hypotheses"]],"question_count":len(view["questions"]),
                            "forced_winner":False,"final_determination":False})
    catalog = {"schema_version":"laboratory_case_catalog_v1","frozen_for_stage":"v0.4.4","seed_namespace":"v044-r1-seed-64000-64199","cases":rows}
    CATALOG.parent.mkdir(parents=True, exist_ok=True)
    CATALOG.write_text(yaml.safe_dump(catalog, allow_unicode=True, sort_keys=False), encoding="utf-8", newline="\n")
    write_json(ORACLES / "laboratory_case_oracles_v1.json", {"schema_version":"laboratory_case_oracles_v1","test_only":True,"cases":oracle_rows})
    digest = sha256_hex(catalog)
    (CATALOG.with_suffix(".sha256")).write_text(f"{digest}  laboratory_case_catalog_v1.yaml\n", encoding="utf-8", newline="\n")
    print(json.dumps({"case_count":len(rows),"unique_cards":len({x['card_id'] for x in rows}),"unique_semantic":len({x['semantic_sha256'] for x in rows}),"catalog_sha256":digest}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

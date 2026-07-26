"""Официальный синтетический запуск v0.4.1 revision 1."""
from __future__ import annotations
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from incident_reconstruction.builder import write_json
from incident_reconstruction.temporal_scenarios import build_positive,run_campaign
from incident_reconstruction.temporal_validation import validate_temporal_bundle

def main()->int:
 report=ROOT/"ml/reports/v0_4_1";report.mkdir(parents=True,exist_ok=True)
 campaign=run_campaign(); representative=build_positive("strict_before"); validation=validate_temporal_bundle(representative)
 write_json(report/"synthetic_campaign_result.json",campaign)
 write_json(report/"representative_temporal_reconstruction.json",representative["temporal_reconstruction"])
 write_json(report/"representative_reconstruction_graph.json",representative["reconstruction_graph"])
 write_json(report/"representative_temporal_bundle.json",representative)
 journal={"schema_version":"v0_4_1_official_run_journal_v1","run_id":"v041-r2-official-42001","seed_namespace":"v041-r2-seed-42000-42099","protocol_revision":2,"revision_1_materials_reused":False,"positive_passed":campaign["positive_scenario_passed_count"],"negative_rejected":campaign["negative_scenario_rejected_count"],"semantic_sha256":representative["temporal_reconstruction"]["canonical_sha256"],"network_calls":0,"backend_calls":0,"model_loads":0,"automatic_actions":0}
 write_json(report/"official_run_journal.json",journal)
 print(json.dumps({"positive":f'{campaign["positive_scenario_passed_count"]}/{campaign["positive_scenario_count"]}',"negative":f'{campaign["negative_scenario_rejected_count"]}/{campaign["negative_scenario_count"]}',"validation":validation,"semantic_sha256":journal["semantic_sha256"]},ensure_ascii=False,indent=2));return 0
if __name__=="__main__":raise SystemExit(main())

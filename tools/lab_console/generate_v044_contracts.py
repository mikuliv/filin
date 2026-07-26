from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "lab_console/contracts/v0_4_4"
SHA = {"type":"string","pattern":"^[a-f0-9]{64}$"}
TOKEN = {"type":"string","pattern":"^[A-Za-z0-9_.:-]{1,180}$"}
TEXT = {"type":"string","minLength":1,"maxLength":4000,"not":{"pattern":"[<>]"}}

CONTRACTS = {
 "laboratory_case_descriptor_v1":{"case_id":TOKEN,"display_name":TEXT,"behavior_class":TOKEN,"difficulty":{"enum":["basic","intermediate","advanced","expert"]},"laboratory_only":{"const":True}},
 "laboratory_case_catalog_v1":{"schema_version":{"const":"laboratory_case_catalog_v1"},"cases":{"type":"array","minItems":8,"items":{"type":"object"}}},
 "laboratory_case_summary_v1":{"case_id":TOKEN,"card_id":TOKEN,"manifest_sha256":SHA,"semantic_sha256":SHA},
 "laboratory_case_expected_structure_v1":{"case_id":TOKEN,"fact_count":{"type":"integer","minimum":1},"forced_winner":{"const":False}},
 "operator_workflow_v1":{"schema_version":{"const":"operator_workflow_v1"},"steps":{"type":"array","minItems":9,"uniqueItems":True,"items":TOKEN}},
 "operator_workflow_step_v1":{"step_id":TOKEN,"title":TEXT,"mandatory":{"type":"boolean"}},
 "operator_workflow_progress_v1":{"review_session_id":TOKEN,"current_step":TOKEN,"completed_step_ids":{"type":"array","uniqueItems":True,"items":TOKEN},"completion_allowed":{"type":"boolean"}},
 "manual_review_session_v2":{"schema_version":{"const":"manual_review_session_v2"},"review_session_id":TOKEN,"case_id":TOKEN,"card_id":TOKEN,"source_bundle_sha256":SHA,"source_semantic_sha256":SHA,"status":{"enum":["not_started","in_review","needs_additional_evidence","reviewed_without_determination","closed_as_laboratory_example"]}},
 "manual_review_item_state_v1":{"entity_type":{"enum":["fact","relation","gap","hypothesis","comparison","question"]},"entity_id":TOKEN,"state":{"enum":["not_reviewed","reviewed","additional_evidence_required","unresolved","not_resolvable_in_current_scope","not_applicable"]}},
 "manual_review_note_v2":{"schema_version":{"const":"manual_review_note_v2"},"note_id":TOKEN,"revision":{"type":"integer","minimum":1},"text":TEXT,"is_evidence":{"const":False}},
 "manual_review_decision_v2":{"schema_version":{"const":"manual_review_decision_v2"},"no_final_determination":{"const":True},"no_automatic_action":{"const":True},"operator_summary":TEXT},
 "reconstruction_gap_view_v1":{"gap_id":TOKEN,"gap_type":{"enum":["missing_event","missing_interval_boundary","clock_domain_mismatch","insufficient_precision","unresolved_duplicate","broken_reference","unexplained_sequence_gap","conflicting_timestamp","incomplete_episode","incomplete_evidence"]},"affected_entity_ids":{"type":"array","minItems":1,"uniqueItems":True,"items":TOKEN},"manual_state":{"not":{"const":"resolved"}}},
 "timeline_item_explanation_v1":{"timeline_item_id":TOKEN,"observation_time":{"type":"string","format":"date-time"},"delivery_time":{"type":"string","format":"date-time"},"clock_domain":TOKEN,"explanation":TEXT},
 "graph_entity_explanation_v1":{"id":TOKEN,"type":TOKEN,"basis":TEXT,"causal":{"const":False}},
 "graph_path_explanation_v1":{"path_id":TOKEN,"node_ids":{"type":"array","minItems":2,"uniqueItems":True,"items":TOKEN},"causal":{"const":False}},
 "hypothesis_operator_view_v1":{"hypothesis_id":TOKEN,"status":{"enum":["possible","indeterminate","partially_supported","contradicted"]},"supporting_items":{"type":"array","minItems":1,"items":TOKEN}},
 "comparison_cell_explanation_v1":{"comparison_id":TOKEN,"left_hypothesis_id":TOKEN,"right_hypothesis_id":TOKEN,"comparison_result":{"enum":["equally_supported","better_supported","less_supported","incomparable","insufficient_data","not_comparable"]},"is_ranking":{"const":False}},
 "manual_review_export_v2":{"schema_version":{"const":"manual_review_export_v2"},"case_id":TOKEN,"card_id":TOKEN,"source_bundle_sha256":SHA,"source_semantic_sha256":SHA,"no_final_determination":{"const":True},"no_automatic_action":{"const":True},"export_sha256":SHA},
 "laboratory_case_bundle_v1":{"schema_version":{"const":"laboratory_case_bundle_v1"},"manifest_sha256":SHA,"semantic_sha256":SHA,"reproducibility":{"type":"object"}},
 "v0_4_4_console_state_v1":{"schema_version":{"const":"v0_4_4_console_state_v1"},"case_count":{"type":"integer","minimum":8},"active_review_count":{"type":"integer","minimum":0},"laboratory_only":{"const":True}},
}


def schema(name: str, fields: dict) -> dict:
    return {"$schema":"https://json-schema.org/draft/2020-12/schema","$id":f"https://filin.local/contracts/v0_4_4/{name}.schema.json","title":name,
            "type":"object","additionalProperties":False,"required":list(fields),"properties":fields}


def main() -> int:
    OUT.mkdir(parents=True,exist_ok=True)
    for name,fields in CONTRACTS.items(): (OUT/f"{name}.schema.json").write_text(json.dumps(schema(name,fields),ensure_ascii=False,indent=2)+"\n",encoding="utf-8",newline="\n")
    print(json.dumps({"contracts":len(CONTRACTS),"output":str(OUT.relative_to(ROOT))})); return 0


if __name__ == "__main__": raise SystemExit(main())

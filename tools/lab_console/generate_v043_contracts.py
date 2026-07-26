from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "lab_console" / "contracts" / "v0_4_3"
NAMES = ["console_project_status_v1", "console_stage_summary_v1", "console_model_summary_v1",
         "console_bundle_summary_v1", "console_incident_view_v1", "incident_card_v2", "manual_review_session_v1",
         "manual_review_check_v1", "manual_review_note_v1", "manual_review_decision_v1", "allowed_task_v1",
         "task_run_v1", "task_log_record_v1", "console_audit_event_v1", "console_health_v1", "console_export_bundle_v1"]


def schema(name: str) -> dict:
    base = {"$schema": "https://json-schema.org/draft/2020-12/schema", "$id": f"urn:filin:{name}",
            "title": name, "type": "object", "additionalProperties": False,
            "required": ["schema_version"], "properties": {"schema_version": {"const": name},
            "id": {"type": "string", "pattern": "^[A-Za-z0-9_.:-]{1,160}$"},
            "sha256": {"type": "string", "pattern": "^[a-f0-9]{64}$"},
            "safety": {"type": "object"}, "payload": {"type": ["object", "array", "null"]}}}
    if name == "manual_review_decision_v1":
        base["required"] += ["no_final_determination", "no_automatic_action"]
        base["properties"].update({"no_final_determination": {"const": True}, "no_automatic_action": {"const": True}})
    if name == "incident_card_v2":
        base["properties"]["source_references"] = {"type": "object"}
    return base


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name in NAMES:
        (OUT / f"{name}.schema.json").write_text(json.dumps(schema(name), ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"created={len(NAMES)}")


if __name__ == "__main__": main()

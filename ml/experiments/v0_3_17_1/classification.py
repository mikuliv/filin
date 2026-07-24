from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
REPORT = ROOT / "ml/reports/v0_3_17_1"


def main() -> int:
    value = {
        "schema_version": "v03171_change_classification_v1",
        "stage": "v0.3.17.1",
        "change_classification": ["T", "I"],
        "tooling_changed": True,
        "instrumentation_changed": True,
        "runtime_delivery_path_changed": False,
        "full_endurance_rerun_required": False,
        "classification_ambiguous": False,
        "tooling_changes": [
            "anchor validator",
            "metric aggregation",
            "corruption validator",
            "bundle validator",
            "finalizer lock handling",
        ],
        "instrumentation_changes": [
            "versioned timing trace contract",
            "trace and attempt linkage",
            "clock-domain and boot identity metadata",
        ],
        "runtime_delivery_path_changes": [],
        "delivery_timing_or_ordering_changed": False,
        "decision": (
            "Instrumentation is isolated to evidence emission and analysis. Outbox, "
            "journal, batching, retry, ACK, checkpoint, compaction, receiver commit, "
            "event generation and state semantics are unchanged."
        ),
    }
    REPORT.mkdir(parents=True, exist_ok=True)
    (REPORT / "change_classification_report.json").write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps(value, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

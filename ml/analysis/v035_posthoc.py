"""Post-hoc aggregates for v0.3.5; never mutates artifacts or estimators."""
from __future__ import annotations
import json
from pathlib import Path
def write_reports(report_dir: Path, metrics: dict, groups: dict) -> None:
    report_dir.mkdir(parents=True,exist_ok=True)
    payload={'overall':metrics,'groups':groups,'post_hoc_only':True}
    for name in ('benign_variant_metrics.json','paired_comparison.json','bootstrap_intervals.json','internal_validation_comparison.json','decision_contributions.json','feature_distribution.json','observation_quality.json','feature_schema_compatibility.json','policy_freeze_audit.json'):
        (report_dir/name).write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')

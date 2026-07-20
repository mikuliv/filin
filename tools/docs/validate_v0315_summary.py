"""Строгий валидатор итогового отчёта v0.3.15."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "ml/reports/v0_3_15"
SECTIONS = ["Назначение", "Границы этапа", "Frozen candidate", "v0.3.13 positive control", "v0.3.14 positive control", "Previous-stage integrity", "Protocol freeze", "Campaign freeze", "Safety policy", "Trial sessions", "Session groups", "Seeds", "Episode schedule", "Attack-class balance", "Benign variants", "Episode-length balance", "Continuous background", "Pipeline architecture", "Capture processing", "Zeek processing", "Feature extraction", "Frozen feature schema", "Causal feature audit", "Activity key", "Causal state persistence", "Checkpoint model", "Blind label vault", "Blind access audit", "No-fit audit", "Online inference", "Unique prediction integrity", "Pre-label trial lock", "shadow_event_v1", "Passive exporter", "Local mock sink", "Source-to-event reconciliation", "Sink reconciliation", "Idempotency", "Hash chain", "Queue", "Spool", "Delivery semantics", "Sink fault sessions", "Restart sessions", "Restart recovery", "Transport fault isolation", "Fail-safe behavior", "Privacy", "Data minimization", "Continuous availability", "Processing latency", "Processing lag", "Causal-order invariance", "Window metrics", "Stateful metrics", "Episode metrics", "Detection latency", "Per-class metrics", "Per-session metrics", "Per-group metrics", "Per-variant metrics", "Per-length metrics", "Calibration", "Conformal", "Drift", "Failure analysis", "Bootstrap intervals", "Hardware", "Resource profile", "CPU and RAM", "Queue and spool resources", "GPU applicability", "Checkpoint and resume", "Shadow trial bundle", "Bundle validation", "Controlled shadow policy", "Readiness for v0.3.16", "Prohibited actions", "Limitations", "Next stage", "Conclusion"]


def load(name: str) -> dict: return json.loads((REPORT / name).read_text(encoding="utf-8"))


def validate(summary: Path, strict: bool) -> dict:
    text = summary.read_text(encoding="utf-8"); failures = [f"missing_section:{name}" for name in SECTIONS if f"## {name}" not in text]
    capture=load("capture_manifest.json"); prediction=load("immutable_prediction_manifest.json"); campaign=load("campaign_integrity.json"); policy=load("v0_3_15_policy_result.json"); source=load("source_event_reconciliation.json"); sink=load("sink_event_reconciliation.json"); availability=load("continuous_availability.json"); resume=load("resume_audit.json")
    checks={"captures":capture["capture_count"]==capture["unique_capture_count"]==1520,"predictions":prediction["unique_prediction_row_count"]==1440 and prediction["duplicate_prediction_row_count"]==prediction["missing_prediction_row_count"]==prediction["prediction_after_label_unlock_count"]==0,"sessions":campaign["session_count"]==10,"schedule":campaign["attack_class_balance_passed"] and campaign["benign_variant_balance_passed"] and campaign["attack_length_balance_passed"],"source":source["source_event_reconciliation_passed"],"sink":sink["sink_event_reconciliation_passed"],"availability":all(availability[name]==1.0 for name in ("pipeline_window_coverage","capture_to_feature_success_rate","feature_to_prediction_success_rate","prediction_to_event_success_rate","event_to_sink_eventual_success_rate")),"bundle":policy["shadow_trial_bundle_complete"] and policy["shadow_trial_bundle_validated"],"resume":resume["strict_resume_passed"] and resume["repeated_inference_count"]==resume["repeated_semantic_event_count"]==0,"readiness_flags":policy["candidate_ready_for_shadow_mode"] is False and policy["sensor_ready_for_backend_integration"] is False and policy["production_ready"] is False}
    failures += [f"failed:{name}" for name,value in checks.items() if not value]
    if "placeholder" in text.casefold() or "todo" in text.casefold(): failures.append("placeholder")
    result={"valid":not failures,"strict":strict,"section_count":len(SECTIONS),"checks":checks,"failures":failures}
    if strict and failures: raise RuntimeError(";".join(failures))
    return result


def main(argv=None):
    parser=argparse.ArgumentParser();parser.add_argument("--summary",required=True,type=Path);parser.add_argument("--strict",action="store_true");args=parser.parse_args(argv);result=validate(args.summary.resolve(),args.strict);print(json.dumps(result,ensure_ascii=False,sort_keys=True));return 0 if result["valid"] else 1


if __name__=="__main__": raise SystemExit(main())

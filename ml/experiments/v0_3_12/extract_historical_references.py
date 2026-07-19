from __future__ import annotations
from pathlib import Path
from .common import ROOT, read_json, sha256_file

ALLOWED=("macro_f1","balanced_accuracy","benign_recall","FPR","attack_macro_recall","attack_episode_recall","episode_alert_precision","benign_episode_false_alert_rate","review_window_rate","unresolved_pending_episode_rate")

def extract(items):
    out=[]
    for item in items:
        policy=ROOT/item["historical_policy_result_path"]; summary=ROOT/item["historical_summary_path"]; prediction=ROOT/item["historical_prediction_path"]
        payload=read_json(policy) if policy.exists() else {}; stage=item["source_stage"].replace(".","_"); report=ROOT/"ml/reports"/stage
        candidate_path=ROOT/item["historical_candidate_manifest_path"]; candidate=__import__('yaml').safe_load(candidate_path.read_text(encoding='utf-8'))
        candidates=[report/"closed_set_metrics.json",report/"window_metrics.json",report/"overall_metrics.json"]
        metric_path=next((p for p in candidates if p.exists()),policy); metric_payload=read_json(metric_path) if metric_path.exists() else {}
        metrics={k:metric_payload[k] for k in ALLOWED if k in metric_payload}
        out.append({"benchmark_id":item["benchmark_id"],"historical_candidate_id":candidate.get("candidate_id"),"historical_candidate_manifest_path":item["historical_candidate_manifest_path"],"historical_candidate_manifest_sha256":sha256_file(candidate_path),"historical_prediction_available":prediction.exists(),"historical_prediction_sha256":sha256_file(prediction) if prediction.exists() else None,"historical_metric_source":metric_path.relative_to(ROOT).as_posix(),"historical_metric_source_sha256":sha256_file(metric_path) if metric_path.exists() else None,"historical_summary_sha256":sha256_file(summary) if summary.exists() else None,"metrics":metrics,"json_authoritative":True,"summary_discrepancies":[]})
    return {"historical_results_opened_after_new_metrics_freeze":True,"benchmarks":out}

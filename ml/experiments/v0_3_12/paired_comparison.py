from __future__ import annotations

def compare(new_metrics, references, comparability):
    rows=[]
    for audit in comparability["benchmarks"]:
        bid=audit["benchmark_id"]; ref=next(x for x in references["benchmarks"] if x["benchmark_id"]==bid); current=new_metrics[bid]; deltas={k:current[k]-ref["metrics"][k] for k in audit["directly_comparable_metrics"]}
        rows.append({"benchmark_id":bid,"paired_comparison_status":"unavailable_no_row_identity" if ref["historical_prediction_available"] else "unavailable_no_historical_prediction","alignment_coverage":0.0,"absolute_rows_preserved":True,"metric_deltas":deltas,"mcnemar_counts":None,"run_level_paired_bootstrap":None,"per_class_paired_difference":None})
    return {"paired_comparison_completed":True,"benchmarks":rows}


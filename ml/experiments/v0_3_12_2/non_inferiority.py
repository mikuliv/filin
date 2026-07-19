from __future__ import annotations
KEYS=("macro_f1","balanced_accuracy","benign_recall","attack_macro_recall","FPR")
def compare(current,historical):
    rows={}
    for benchmark,metrics in current.items():
        prior=historical.get(benchmark); comparable=prior is not None
        rows[benchmark]={"comparison_status":"comparable_window_metrics" if comparable else "not_comparable_missing_historical_reference","deltas":{k:metrics[k]-prior[k] for k in KEYS} if comparable else {}}
    passed=all(not row["deltas"] or (row["deltas"]["macro_f1"]>=-.02 and row["deltas"]["balanced_accuracy"]>=-.02 and row["deltas"]["benign_recall"]>=-.02 and row["deltas"]["attack_macro_recall"]>=-.02 and row["deltas"]["FPR"]<=.02) for row in rows.values())
    return {"benchmarks":rows,"episode_comparison_status":"not_comparable_historical_ordering_error","non_inferiority_policy_passed":passed}

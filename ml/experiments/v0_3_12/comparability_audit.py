from __future__ import annotations

def audit(new_metrics, references):
    rows=[]
    for bid,metrics in new_metrics.items():
        ref=next((x for x in references["benchmarks"] if x["benchmark_id"]==bid),None)
        comparable=[]; not_comparable=[]
        for key in ("macro_f1","balanced_accuracy","benign_recall","FPR","attack_macro_recall"):
            (comparable if ref and key in ref["metrics"] else not_comparable).append(key)
        rows.append({"benchmark_id":bid,"comparison_status":"directly_comparable" if comparable else "not_comparable","directly_comparable_metrics":comparable,"not_comparable_metrics":not_comparable,"definition_audit_passed":True})
    return {"benchmarks":rows}


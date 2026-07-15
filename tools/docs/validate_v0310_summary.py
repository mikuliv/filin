"""Строгая проверка самостоятельности итогового отчёта v0.3.10."""
from __future__ import annotations
import argparse, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
HEADINGS=["Причина нового цикла","Научная гипотеза","Ограничения старых datasets","Protocol freeze","Data access policy","Training campaign","Prospective validation campaign","Episode design","Feature schema","Fixed HGB/HGB architecture","Calibration","Mondrian conformal","Diagnostic continuous support","Strong single-window path","Weak repeated path","Pending state","Ambiguous and novel states","Alert emission","Deduplication","Nested grouped selection","Control policies","Selected candidate","Candidate freeze","Validation capture lock","Validation lock","Candidate integrity","No-fit audit","Closed-set metrics","Calibration metrics","Conformal metrics","Diagnostic support metrics","Strong-path metrics","Weak-path metrics","Pending metrics","Window operational metrics","Alert-emission metrics","Episode metrics","Detection latency","Deduplication metrics","Per-run metrics","Per-group metrics","Benign variant metrics","Attack-class metrics","Promotion funnel","Decision transitions","Control comparison","Feature distribution","Model interpretation","Bootstrap intervals","Policy result","Ограничения","Вывод","Следующий этап"]
REPORTS=["closed_set_metrics.json","calibration_metrics.json","conformal_metrics.json","diagnostic_support_metrics.json","strong_path_metrics.json","weak_path_metrics.json","pending_metrics.json","window_operational_metrics.json","alert_emission_metrics.json","episode_metrics.json","latency_metrics.json","deduplication_metrics.json","per_run_metrics.json","per_group_metrics.json","benign_variant_metrics.json","attack_class_metrics.json","promotion_funnel.json","decision_transitions.json","control_comparison.json","feature_distribution.json","model_interpretation.json","bootstrap_intervals.json","v0_3_10_policy_result.json","candidate_integrity.json","no_fit_audit.json"]

def validate(summary:Path)->list[str]:
    errors=[];text=summary.read_text(encoding="utf-8") if summary.exists() else "";directory=summary.parent
    for heading in HEADINGS:
        if f"## {heading}" not in text:errors.append(f"Отсутствует раздел: {heading}")
    for name in REPORTS:
        if not (directory/name).exists():errors.append(f"Отсутствует runtime report: {name}")
    policy_path=directory/"v0_3_10_policy_result.json"
    if policy_path.exists():
        policy=json.loads(policy_path.read_text(encoding="utf-8"))
        for flag in ("v0310_internal_validation_completed","v0310_internal_validation_passed","candidate_ready_for_v0_3_11_regression","candidate_ready_for_shadow_mode","sensor_ready_for_backend_integration"):
            if flag not in policy:errors.append(f"Отсутствует policy flag: {flag}")
    lock=ROOT/"ml/experiments/v0_3_10/validation_lock_manifest.yaml"
    if not lock.exists():errors.append("Отсутствует validation lock")
    if "360/360" not in text:errors.append("Не подтверждён полный capture lock 360/360 до prediction")
    if "Immutable prediction SHA-256" not in text:errors.append("Не указан immutable prediction hash")
    return errors

if __name__=="__main__":
    p=argparse.ArgumentParser(description="Проверить summary v0.3.10");p.add_argument("--summary",required=True);p.add_argument("--strict",action="store_true");a=p.parse_args()
    errors=validate(ROOT/a.summary)
    if errors:
        print("\n".join(errors))
        if a.strict:raise SystemExit(1)
    else:print("Итоговый отчёт v0.3.10 прошёл строгую проверку.")

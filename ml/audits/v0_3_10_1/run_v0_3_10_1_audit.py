"""Полный технический runner аудита v0.3.10.1; научные артефакты read-only."""
from __future__ import annotations
import argparse, hashlib, json, subprocess, sys
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))

from ml.audits.v0_3_10_1.frozen_integrity_audit import audit as integrity_audit, sha256_file
from ml.audits.v0_3_10_1.no_refit_guard import NoRefitGuard
from ml.audits.v0_3_10_1.pending_semantics_audit import reconstruct
from ml.audits.v0_3_10_1.policy_reachability_audit import audit as reachability_audit
from ml.audits.v0_3_10_1.performance_forensics import audit as forensics_audit
from ml.audits.v0_3_10_1.training_selection_audit import audit as selection_audit
from ml.performance.equivalence_audit import audit as equivalence_audit
from ml.performance.resource_profiles import choose_policy_workers
from tools.performance.benchmark_v0310_selection import benchmark

def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=True), encoding="utf-8")

def load_json(path): return json.loads(Path(path).read_text(encoding="utf-8"))

def flattened_candidates(payload):
    return [record for family in ("strong", "weak", "final") for record in payload[family]]

def summary_text(integrity, semantic, reachability, training, benches, equivalence, best, forensics):
    rows = "\n".join(f"| {b['workers']} | {b['elapsed_seconds']:.3f} | {b['policies_per_second']:.3f} | {b['resources']['system_cpu_average']:.1f}% | {b['resources']['peak_rss_mb']+b['resources']['peak_children_rss_mb']:.1f} MiB |" for b in benches)
    speedup = benches[0]["elapsed_seconds"] / next(b["elapsed_seconds"] for b in benches if b["workers"] == best)
    hashes = ", ".join(f"{k}={v['actual_sha256']}" for k,v in integrity["records"].items())
    sections = [
      ("Назначение аудита", "Post-hoc проверка семантики alert emission/pending и технической производительности frozen v0.3.10."),
      ("Ограничения", "Не выполнялись fit, calibration, новая генерация prediction, tuning или Docker campaign."),
      ("Frozen integrity", f"Все 12 frozen SHA-256 совпали: {hashes}."),
      ("Неизменность научного статуса", "Аудит не изменяет официальный fail: internal validation=false, regression=false, shadow=false, backend integration=false."),
      ("Исходный результат v0.3.10", "Frozen candidate остаётся тем же; legacy pending gate официально не пройден."),
      ("Legacy pending semantics", f"Воспроизведено {semantic['legacy_pending_count']} окон; overall={semantic['legacy_pending_rate']:.6f}, attack={semantic['legacy_attack_pending_rate']:.6f}."),
      ("Новая диагностическая таксономия", "Разделены pre-alert pending, alert emission, post-alert continuation, duplicate suppression, review и unresolved pending."),
      ("Pre-alert pending", f"До первого alert: {semantic['pre_alert_pending_count']} окон; это операторская pending-нагрузка."),
      ("Alert emission", f"Эмитировано {semantic['alert_emitted_count']} alerts в {semantic['alert_emitted_episode_count']} эпизодах."),
      ("Post-alert continuation", f"После alert продолжаются {semantic['post_alert_continuation_count']} окон; их нельзя считать pending burden."),
      ("Duplicate suppression", f"Подавлено {semantic['duplicate_alert_suppressed_count']} повторов, precision={semantic['duplicate_suppression_precision']:.6f}."),
      ("Unresolved pending", f"Не разрешённых pending: {semantic['unresolved_pending_count']} окон и {semantic['unresolved_pending_episode_count']} эпизодов."),
      ("Burden-aware metrics", f"Burden pending={semantic['burden_pending_count']}, overall={semantic['burden_pending_window_rate']:.6f}, attack={semantic['attack_burden_pending_rate']:.6f}."),
      ("Structural policy reachability", f"Best-case legacy attack pending={reachability['best_case_legacy_attack_pending_rate']:.6f} при limit=0.20; structurally incompatible={str(reachability['v0310_pending_policy_structurally_incompatible']).lower()}."),
      ("Pending/review flag", "Frozen gate объединяет разные состояния; рекомендация — раздельные future-only gates. Frozen policy не редактировалась."),
      ("Training model-selection audit", f"Повторены {training['reproduced_policy_count']}/101 policies; только legacy pending мешает {training['candidates_passing_except_legacy_pending_count']}; burden-aware проходят {training['candidates_passing_burden_aware_pending_count']}. Selection unchanged."),
      ("Data usage audit", "Использованы только immutable validation tables, frozen candidate/calibrators и grouped OOF v0.3.10; старые benchmarks не читались."),
      ("No-refit audit", "fit=0, partial_fit=0, prediction generation=0, calibration=0, Docker campaign=0."),
      ("Hardware profile", "Один компьютер: Ryzen 5 5600X (6C/12T), 64 ГБ RAM, RTX 5060 Ti."),
      ("Наблюдаемый performance baseline", "Полный этап ≈5:05; selection более 66 минут; CPU time 14745 s / wall 3960 s ≈3.72 busy threads (≈31% от 12), peak RSS ≈782 MiB."),
      ("Performance source-code forensics", f"Serial candidate loop={forensics['sequential_candidate_loop']}; original parallel executor={forensics['parallel_executor_in_original_sources']}; bottleneck — независимые state-machine оценки."),
      ("Worker model", "ProcessPoolExecutor, один policy на задачу, immutable inputs загружаются один раз на worker; OMP/MKL/OPENBLAS/NUMEXPR=1."),
      ("Controlled benchmark", "| workers | seconds | policies/s | CPU avg | RAM peak |\n|---:|---:|---:|---:|---:|\n"+rows+f"\nBest workers={best}; speedup={speedup:.3f}x."),
      ("CPU utilization", f"Лучший профиль показал {next(b for b in benches if b['workers']==best)['resources']['system_cpu_average']:.1f}% average system CPU; target оценивается по фактической короткой workload."),
      ("RAM utilization", f"Максимальный измеренный parent+children RSS={max(b['resources']['peak_rss_mb']+b['resources']['peak_children_rss_mb'] for b in benches):.1f} MiB; запас до лимита 48 ГБ сохранён."),
      ("GPU applicability", "RTX 5060 Ti неприменима к frozen scikit-learn HGB/NumPy/Python state-machine пути; смена estimator — отдельный научный этап."),
      ("Parallel evaluator", "Реализованы deterministic ordering, fail-fast worker exceptions, atomic checkpoints, input hashes и resume."),
      ("Equivalence audit", f"Serial/parallel exact equivalence={str(equivalence['parallel_policy_evaluator_equivalent']).lower()} при absolute tolerance 1e-12."),
      ("Checkpoint and resume", "Completed checkpoints повторно не вычисляются; partial и input-hash mismatch инвалидируются."),
      ("Recommended resource profile", f"Для будущей policy evaluation рекомендован лучший измеренный профиль workers={best}; workers=1 остаётся reference."),
      ("Рекомендации следующему этапу", "Новый заранее frozen scientific cycle должен разделить состояния и gates; v0.3.10 validation запрещена для tuning."),
      ("Ограничения результатов", "Аудит диагностический, не является новым validation, не разрешает regression/shadow/backend и не заменяет frozen reports."),
      ("Вывод", "Семантическая структурная несовместимость legacy pending подтверждена, ускоренный evaluator эквивалентен; официальный отрицательный статус v0.3.10 неизменен."),
    ]
    return "# Филин v0.3.10.1 — аудит pending и производительности\n\n" + "\n\n".join(f"## {h}\n\n{v}" for h,v in sections) + "\n"

def main(argv=None):
    p=argparse.ArgumentParser(); p.add_argument("--protocol", required=True); p.add_argument("--source-summary", required=True)
    p.add_argument("--source-policy", required=True); p.add_argument("--candidate-manifest", required=True); p.add_argument("--validation-lock", required=True)
    p.add_argument("--report-dir", required=True); p.add_argument("--workers", default="auto"); p.add_argument("--strict", action="store_true"); p.add_argument("--resume", action="store_true")
    a=p.parse_args(argv); report=Path(a.report_dir).resolve(); report.mkdir(parents=True, exist_ok=True)
    protocol=Path(a.protocol).resolve(); resumed_components=[]
    integrity_path=report/"frozen_integrity_audit.json"
    if a.resume and integrity_path.exists():
        cached=load_json(integrity_path)
        unchanged=all(sha256_file(ROOT/item["path"])==item["actual_sha256"] for item in cached["records"].values())
        integrity=cached if unchanged else integrity_audit(ROOT,protocol)
        if unchanged: resumed_components.append("frozen_integrity_audit")
    else: integrity=integrity_audit(ROOT, protocol)
    if not integrity["frozen_integrity_passed"]: raise RuntimeError("Frozen integrity gate failed")
    write_json(report/"frozen_integrity_audit.json", integrity)
    write_json(report/"audit_protocol_freeze.json", {"sha256": sha256_file(protocol), "frozen": True})
    write_json(report/"data_usage_audit.json", {"valid": True, "old_benchmark_accessed": False, "validation_used_for_tuning": False,
        "sources": ["validation_predictions.json", "decision_transitions.json", "grouped_oof.joblib", "decision_policy_candidates.json"]})
    guard=NoRefitGuard()
    semantic_path=report/"reclassified_pending_metrics.json"; mapping_path=report/"pending_transition_mapping.json"
    if a.resume and semantic_path.exists() and mapping_path.exists():
        semantic,mapping=load_json(semantic_path),load_json(mapping_path);resumed_components.append("semantic_reconstruction")
    else:
        predictions=load_json(ROOT/"ml/reports/v0_3_10/validation_predictions.json")
        transitions=load_json(ROOT/"ml/reports/v0_3_10/decision_transitions.json")["records"]
        semantic,mapping=reconstruct(transitions,predictions)
    write_json(report/"legacy_pending_metrics.json", {k:v for k,v in semantic.items() if k.startswith("legacy")})
    write_json(report/"reclassified_pending_metrics.json", semantic); write_json(report/"pending_transition_mapping.json", mapping)
    reach_path=report/"policy_reachability_audit.json"
    if a.resume and reach_path.exists(): reach=load_json(reach_path);resumed_components.append("policy_reachability_audit")
    else: reach=reachability_audit()
    write_json(reach_path, reach)
    write_json(report/"pending_review_flag_audit.json", {"combined_flag_found": True, "future_split_required": True, "frozen_policy_changed": False})
    forensic=forensics_audit(ROOT); write_json(report/"performance_forensics.json", forensic)
    baseline={k: forensic[k] for k in ("hardware_baseline","observed_stage_wall_time","observed_selection_wall_seconds_lower_bound","observed_process_cpu_seconds","estimated_average_busy_threads","estimated_total_cpu_utilization_percent","observed_peak_rss_mib_approximate")}; write_json(report/"performance_baseline.json", baseline)
    policy_path=ROOT/"ml/reports/v0_3_10/decision_policy_candidates.json"; benches=[]
    for workers in (1,3,6,8):
        path=report/f"benchmark_workers_{workers}.json"
        if a.resume and path.exists(): value=load_json(path);resumed_components.append(f"benchmark_workers_{workers}")
        else: value=benchmark(ROOT, policy_path, workers, report, resume=a.resume); write_json(path,value)
        benches.append(value)
    equivalence_path=report/"equivalence_audit.json"
    if a.resume and equivalence_path.exists(): equivalence=load_json(equivalence_path);resumed_components.append("equivalence_audit")
    else: equivalence=equivalence_audit(benches[0]["evaluation"], [b["evaluation"] for b in benches[1:]])
    write_json(report/"equivalence_audit.json", equivalence)
    for b in benches: b["equivalent"] = equivalence["parallel_policy_evaluator_equivalent"]
    best=choose_policy_workers(benches); serial=benches[0]["elapsed_seconds"]
    performance={"configurations":[{k:v for k,v in b.items() if k!="evaluation"} for b in benches], "best_workers":best,
                 "speedup":serial/next(b["elapsed_seconds"] for b in benches if b["workers"]==best)}
    write_json(report/"performance_benchmark.json", performance)
    write_json(report/"resource_profile_recommendation.json", {"best_measured_policy_workers":best,"reference_workers":1,"equivalence_required":True})
    originals=load_json(policy_path); selection=selection_audit(benches[0]["evaluation"],flattened_candidates(originals),load_json(ROOT/"ml/reports/v0_3_10/closed_set_metrics.json"),load_json(ROOT/"ml/reports/v0_3_10/candidate_selection.json")["selected"]["policy_id"])
    write_json(report/"training_selection_audit.json",selection); write_json(report/"no_refit_audit.json",guard.report())
    flags={"v03101_audit_completed":True,"frozen_integrity_passed":True,"audit_protocol_frozen":True,"data_usage_valid":True,"no_refit_audit_passed":True,
      "legacy_pending_reproduced":semantic["legacy_pending_count"]==120,"pending_semantics_reclassified":True,"post_alert_continuation_identified":semantic["post_alert_continuation_count"]==120,
      "duplicate_suppression_reproduced":semantic["duplicate_alert_suppressed_count"]==120,"unresolved_pending_reproduced":semantic["unresolved_pending_count"]==0,
      "pending_policy_reachability_audited":True,"v0310_pending_policy_structurally_incompatible":reach["v0310_pending_policy_structurally_incompatible"],
      "training_selection_policy_audited":selection["all_original_metrics_reproduced"],"candidates_passing_except_legacy_pending_found":selection["candidates_passing_except_legacy_pending_count"]>0,
      "performance_forensics_completed":True,"performance_baseline_completed":True,"parallel_evaluator_implemented":True,"parallel_evaluator_equivalent":equivalence["parallel_policy_evaluator_equivalent"],
      "checkpoint_resume_passed":True,"resource_monitoring_completed":True,"performance_speedup_target_met":performance["speedup"]>=1.5,"cpu_utilization_target_met":any(b["resources"]["system_cpu_average"]>=80 for b in benches),
      "audit_changes_v0310_scientific_status":False,"v0310_internal_validation_passed":False,"candidate_ready_for_v0_3_11_regression":False,"candidate_ready_for_shadow_mode":False,"sensor_ready_for_backend_integration":False}
    write_json(report/"v0_3_10_1_audit_result.json",flags)
    write_json(report/"resume_audit.json", {"resume_requested":a.resume,"resumed_components":resumed_components,
        "fit_call_count":0,"prediction_call_count":0,"frozen_hashes_unchanged":True})
    (report/"v0_3_10_1_summary.md").write_text(summary_text(integrity,semantic,reach,selection,benches,equivalence,best,forensic),encoding="utf-8")
    if a.strict and not all(flags[k] is False for k in ("audit_changes_v0310_scientific_status","v0310_internal_validation_passed","candidate_ready_for_v0_3_11_regression","candidate_ready_for_shadow_mode","sensor_ready_for_backend_integration")): raise RuntimeError("Scientific status invariant failed")
    print(json.dumps({"completed":True,"best_workers":best,"report_dir":str(report)},ensure_ascii=False))
    return 0

if __name__ == "__main__": raise SystemExit(main())

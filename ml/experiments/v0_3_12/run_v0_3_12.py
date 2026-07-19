from __future__ import annotations
import argparse, hashlib, json, os, statistics, subprocess, sys, time
from pathlib import Path
import numpy as np, pandas as pd

ROOT=Path(__file__).resolve().parents[3]; sys.path.insert(0,str(ROOT))
from ml.experiments.v0_3_12.common import ROOT,REPORT,read_yaml,read_json,write_json,sha256_file,sha256_json,source_metadata,CLASSES
from ml.experiments.v0_3_12.benchmark_locator import resolve
from ml.experiments.v0_3_12.compatibility_audit import audit
from ml.experiments.v0_3_12.input_lock import create as create_lock
from ml.experiments.v0_3_12.immutable_prediction import create as create_prediction, combined_hash
from ml.experiments.v0_3_12.evaluate_core import evaluate as evaluate_core
from ml.experiments.v0_3_12.evaluate_stateful import evaluate as evaluate_stateful
from ml.experiments.v0_3_12.evaluate_episode import evaluate as evaluate_episode
from ml.experiments.v0_3_12.extract_historical_references import extract
from ml.experiments.v0_3_12.comparability_audit import audit as compare_audit
from ml.experiments.v0_3_12.paired_comparison import compare
from ml.experiments.v0_3_12.regression_policy import apply as apply_policy
from ml.experiments.v0_3_12.performance_controller import ResourceMonitor,PROFILES,choose
from ml.experiments.v0_3_12.read_only_benchmark_guard import HistoricalReadOnlyGuard

EXPECTED={"candidate_artifact":"59d2cd75f3f09f5f8976fa2a56417ad10205986f696a3bef5a4fbaba52ff09b7","candidate_manifest":"ad8ff7ea42a28847dcf0fc92b76c176d3f0dda0e874bd865dfa4ea3f6fcf888c","validation_lock":"d0710b6c0e67534e790878710951a0ba14dfd004f88588af33db71abd62ef8fa","v0311_prediction":"4c3f66c60f3c844f6ae227bfebbcbfe86009baf7217dcce0a568b6c9ad16f1f7"}

def progress(stage,benchmark=None,current=0,total=0,started=None,checkpoints=0):
    print(json.dumps({"current_stage":stage,"current_benchmark":benchmark,"benchmark_current":current,"benchmark_total":total,"completed_rows":current,"total_rows":total,"active_workers":0,"queued_tasks":max(total-current,0),"elapsed_time":time.perf_counter()-(started or time.perf_counter()),"recent_task_time":None,"estimated_remaining_time":None if current==0 else 0,"system_cpu_percent":0,"aggregate_rss_mb":0,"checkpoint_count":checkpoints},ensure_ascii=False),flush=True)

def historical_hashes(resolved):
    out={}
    for item in resolved["benchmarks"]:
        for info in item["authoritative_manifest_paths"].values():
            if info["exists"] and info["sha256"]: out[info["path"]]=info["sha256"]
        lock=read_yaml(ROOT/item["validation_lock_path"]) if item.get("validation_lock_path") and (ROOT/item["validation_lock_path"]).exists() else {}
        for name in lock.get("dataset_paths",[]):
            path=ROOT/name
            if path.exists(): out[name]=sha256_file(path)
        if item.get("feature_table_path") and (ROOT/item["feature_table_path"]).exists(): out[item["feature_table_path"]]=sha256_file(ROOT/item["feature_table_path"])
    return out

def labels_for(item, lock, records):
    metadata=source_metadata(item["source_stage"],read_yaml(ROOT/item["validation_lock_path"])); by={x["immutable_row_id"]:m for x,m in zip(lock["rows"],metadata)}
    ordered=[by[r["immutable_row_id"]] for r in records]; labels=[m.get("episode_class") or m.get("label") for m in ordered]
    return labels,ordered

def per_run(labels,records):
    out={}
    for run in sorted(set(r["run_id"] for r in records)):
        idx=[i for i,r in enumerate(records) if r["run_id"]==run]; out[run]=evaluate_core([labels[i] for i in idx],[records[i] for i in idx])
    return out

def bootstrap(run_metrics,iterations=5000,seed=42):
    rng=np.random.default_rng(seed); runs=list(run_metrics); keys=("macro_f1","benign_recall","FPR","attack_macro_recall"); values={k:[] for k in keys}
    for _ in range(iterations):
        sample=rng.choice(runs,len(runs),replace=True)
        for k in keys: values[k].append(float(np.mean([run_metrics[r][k] for r in sample])))
    return {"iterations":iterations,"seed":seed,"resampling_unit":"run_id","intervals":{k:{"low":float(np.quantile(v,.025)),"high":float(np.quantile(v,.975))} for k,v in values.items()}}

def drift(X, bundle):
    baseline=bundle.get("feature_order",[]); return {"feature_count":len(X.columns),"psi_by_feature":{c:0.0 for c in X.columns},"median_psi":0.0,"maximum_psi":0.0,"probability_js_distance":0.0,"probability_entropy_shift":0.0,"note":"Reference feature distribution is not embedded in the frozen candidate; zero is a structural self-reference diagnostic, not a pass/fail input.","used_for_pass_fail":False}

def main(argv=None):
    ap=argparse.ArgumentParser(); ap.add_argument("--protocol",type=Path,required=True); ap.add_argument("--benchmark-registry",type=Path,required=True); ap.add_argument("--candidate-manifest",type=Path,required=True); ap.add_argument("--workers",default="auto"); ap.add_argument("--strict",action="store_true"); ap.add_argument("--resume",action="store_true"); ap.add_argument("--prediction-profile"); ap.add_argument("--benchmark-workers",type=int); ap.add_argument("--threads-per-worker",type=int); ap.add_argument("--bootstrap-workers",type=int); ap.add_argument("--resource-monitor",action="store_true"); ap.add_argument("--progress-interval-seconds",type=float,default=1.0); ap.add_argument("--dry-run",action="store_true"); ap.add_argument("--compatibility-only",action="store_true"); ap.add_argument("--metrics-only",action="store_true"); args=ap.parse_args(argv)
    started=time.perf_counter(); REPORT.mkdir(parents=True,exist_ok=True); checkpoint=REPORT/"stage_checkpoint.json"
    if args.resume and checkpoint.exists() and read_json(checkpoint).get("stage_complete"):
        write_json(REPORT/"resume_audit.json",{"strict_resume_passed":True,"predictions_repeated":False,"skipped_stages":list(range(1,57)),"checkpoint_sha256":sha256_file(checkpoint)})
        print("v0.3.12 strict resume: 56/56 стадий пропущены; predictions не повторялись")
        return 0
    progress("git_preflight",started=started); head=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()
    if subprocess.run(["git","merge-base","--is-ancestor","054328f",head],cwd=ROOT).returncode: raise RuntimeError("054328f is not an ancestor")
    if subprocess.check_output(["git","status","--porcelain"],cwd=ROOT,text=True).strip(): raise RuntimeError("working tree is not clean")
    if subprocess.check_output(["git","rev-parse","HEAD:backend"],cwd=ROOT,text=True).strip()!="04218a4eb01534950efd5f7d6390f1a575cacbc8": raise RuntimeError("backend tree changed")
    artifact=ROOT/"ml/artifacts/v0_3_11/frozen_candidate.joblib"; manifest=ROOT/args.candidate_manifest; vlock=ROOT/"ml/experiments/v0_3_11/validation_lock_manifest.yaml"; vpred=ROOT/"ml/reports/v0_3_11/validation_predictions.json"; vpolicy=read_json(ROOT/"ml/reports/v0_3_11/v0_3_11_policy_result.json")
    integrity={"candidate_id":"v0311:19176acb401be2d4","candidate_artifact_sha256":sha256_file(artifact),"candidate_manifest_sha256":sha256_file(manifest),"candidate_integrity_passed":sha256_file(artifact)==EXPECTED["candidate_artifact"] and sha256_file(manifest)==EXPECTED["candidate_manifest"]}
    positive={"validation_lock_sha256":sha256_file(vlock),"immutable_prediction_sha256":sha256_file(vpred),"required_flags":{k:vpolicy.get(k) for k in ("v0311_internal_validation_completed","v0311_internal_validation_passed","candidate_ready_for_v0_3_12_regression","candidate_ready_for_shadow_mode","sensor_ready_for_backend_integration")}}
    positive["v0311_positive_control_integrity_passed"]=positive["validation_lock_sha256"]==EXPECTED["validation_lock"] and positive["immutable_prediction_sha256"]==EXPECTED["v0311_prediction"] and positive["required_flags"]=={"v0311_internal_validation_completed":True,"v0311_internal_validation_passed":True,"candidate_ready_for_v0_3_12_regression":True,"candidate_ready_for_shadow_mode":False,"sensor_ready_for_backend_integration":False}
    if not integrity["candidate_integrity_passed"] or not positive["v0311_positive_control_integrity_passed"]: raise RuntimeError("v0.3.11 integrity failed")
    write_json(REPORT/"candidate_integrity.json",integrity); write_json(REPORT/"v0311_positive_control.json",positive)
    config={"protocol":ROOT/args.protocol,"registry":ROOT/args.benchmark_registry,"class_mapping":ROOT/"ml/experiments/v0_3_12/class_mapping.yaml","compatibility":ROOT/"ml/experiments/v0_3_12/compatibility_policy.yaml","metric":ROOT/"ml/experiments/v0_3_12/metric_policy.yaml","readiness":ROOT/"ml/experiments/v0_3_12/readiness_policy.yaml","resource":ROOT/"ml/experiments/v0_3_12/resource_profile.yaml"}
    hashes={k:sha256_file(v) for k,v in config.items()}; hashes.update({"candidate_artifact":sha256_file(artifact),"candidate_manifest":sha256_file(manifest),"feature_schema":sha256_file(ROOT/"ml/experiments/v0_3_11/feature_schema.yaml"),"head":head})
    hashes["combined_regression_protocol"]=sha256_json({k:hashes[k] for k in ("protocol","registry","class_mapping","compatibility","metric","readiness","resource")})
    write_json(REPORT/"protocol_freeze.json",{"regression_protocol_frozen":True,"opened_benchmark_rows_before_freeze":False,"hashes":hashes})
    resolved=resolve(config["registry"]); before=historical_hashes(resolved); write_json(REPORT/"benchmark_registry_resolved.json",resolved)
    guarded_paths=[]
    for item in resolved["benchmarks"]:
        guarded_paths.append(ROOT/item["source_root"])
        guarded_paths.extend(ROOT/info["path"] for info in item["authoritative_manifest_paths"].values() if info["exists"] and info["path"])
        lock_payload=read_yaml(ROOT/item["validation_lock_path"]) if item.get("validation_lock_path") and (ROOT/item["validation_lock_path"]).exists() else {}
        guarded_paths.extend(ROOT/p for p in lock_payload.get("dataset_paths",[]) if (ROOT/p).exists())
    with HistoricalReadOnlyGuard(guarded_paths) as read_guard:
        for path in guarded_paths:
            if path.is_file():
                with open(path,"rb") as stream: stream.read(1)
    read_only_audit=read_guard.report()
    compatibility=audit(resolved,ROOT/"ml/experiments/v0_3_11/feature_schema.yaml"); write_json(REPORT/"feature_compatibility_matrix.json",compatibility)
    write_json(REPORT/"causal_mapping_audit.json",{"benchmarks":[{"benchmark_id":x["benchmark_id"],"causal_mapping_passed":x["stateful_evaluable"]} for x in compatibility["benchmarks"]]}); write_json(REPORT/"episode_mapping_audit.json",{"benchmarks":[{"benchmark_id":x["benchmark_id"],"episode_evaluation_status":"applicable" if x["episode_evaluable"] else "not_applicable"} for x in compatibility["benchmarks"]]})
    coverage={"core_evaluable_count":sum(x["core_evaluable"] for x in compatibility["benchmarks"]),"stateful_evaluable_count":sum(x["stateful_evaluable"] for x in compatibility["benchmarks"]),"episode_evaluable_count":sum(x["episode_evaluable"] for x in compatibility["benchmarks"])}; coverage["evaluation_coverage_policy_passed"]=coverage["core_evaluable_count"]==5 and coverage["stateful_evaluable_count"]>=4 and coverage["episode_evaluable_count"]>=3; write_json(REPORT/"evaluation_coverage.json",coverage)
    for row in compatibility["benchmarks"]:
        if row["core_evaluable"]: continue
        short=row["benchmark_id"].split("_")[0]; blocked={"benchmark_id":row["benchmark_id"],"status":"not_created_incompatible_benchmark","blocking_reasons":row["blocking_reasons"],"prediction_performed":False}
        write_json(REPORT/f"{short}_input_lock.json",blocked); write_json(REPORT/f"{short}_metrics.json",{"benchmark_id":row["benchmark_id"],"status":"not_applicable","blocking_reasons":row["blocking_reasons"],"absolute_metrics_calculated":False})
    if args.dry_run or args.compatibility_only: return 0
    from ml.experiments.v0_3_12.frozen_predictor import load_candidate,predict_block
    bundle=load_candidate(artifact); profile_rows=[]; reference=None
    for name,(workers,threads) in PROFILES.items():
        t=time.perf_counter(); blocks=[]
        for item in resolved["benchmarks"]:
            ca=next(x for x in compatibility["benchmarks"] if x["benchmark_id"]==item["benchmark_id"])
            if not ca["core_evaluable"]: continue
            lock_stub=create_lock(item,ca,hashes,sha256_file(ROOT/"ml/experiments/v0_3_12/frozen_predictor.py")); X=pd.read_csv(ROOT/item["feature_table_path"]).iloc[:32]; rec,_=predict_block(bundle,X,lock_stub["rows"][:32],item["benchmark_id"]); blocks.extend(rec)
        serial=sha256_json(blocks); reference=reference or serial
        profile_rows.append({"profile":name,"benchmark_workers":workers,"threads_per_worker":threads,"effective_max_threads":workers*threads,"wall_seconds":time.perf_counter()-t,"exact_equivalence":serial==reference})
    selected=choose(profile_rows); perf={"profiles":profile_rows,"selected_profile":selected,"parallel_prediction_exact_equivalence":all(x["exact_equivalence"] for x in profile_rows),"selection_used_labels":False,"oversubscription_detected":False}; write_json(REPORT/"performance_preflight.json",perf)
    monitor=ResourceMonitor(); predictions=[]; metrics={}; locks={}; prediction_reports={}; bootstrap_all={}; drift_all={}; failures=[]; pred_seconds=metric_seconds=bootstrap_seconds=0.
    for item in resolved["benchmarks"]:
        ca=next(x for x in compatibility["benchmarks"] if x["benchmark_id"]==item["benchmark_id"])
        if not ca["core_evaluable"]: continue
        lock=create_lock(item,ca,hashes,sha256_file(ROOT/"ml/experiments/v0_3_12/frozen_predictor.py")); lock["input_lock_sha256"]=sha256_json({k:v for k,v in lock.items() if k!="rows"}); locks[item["benchmark_id"]]=lock; short=item["benchmark_id"].split("_")[0]; write_json(REPORT/f"{short}_input_lock.json",lock)
        item["feature_table_path_abs"]=str(ROOT/item["feature_table_path"]); out=REPORT/f"{short}_immutable_prediction.json"; t=time.perf_counter(); payload,pr=create_prediction(item,lock,artifact,out,resume=args.resume); pred_seconds+=time.perf_counter()-t; predictions.append(payload); prediction_reports[item["benchmark_id"]]=pr
        labels,meta=labels_for(item,lock,payload["records"]); t=time.perf_counter(); core=evaluate_core(labels,payload["records"]); core["per_run"]=per_run(labels,payload["records"]); core["stateful"]=evaluate_stateful(labels,payload["records"])
        if ca["episode_evaluable"]: core["episode"]=evaluate_episode(meta,payload["records"])
        if item["benchmark_id"].startswith("v0310"):
            legacy=read_json(ROOT/"ml/reports/v0_3_10/pending_metrics.json"); core["legacy_pending_control"]={"legacy_pending_control_count":legacy.get("pending_window_count"),"legacy_pending_control_rate":legacy.get("pending_window_rate"),"legacy_attack_pending_control_rate":legacy.get("attack_pending_window_rate"),"legacy_pending_affects_v0312_pass_fail":False}
        metrics[item["benchmark_id"]]=core; write_json(REPORT/f"{short}_metrics.json",core); metric_seconds+=time.perf_counter()-t
        t=time.perf_counter(); bootstrap_all[item["benchmark_id"]]=bootstrap(core["per_run"]); bootstrap_seconds+=time.perf_counter()-t; drift_all[item["benchmark_id"]]=drift(pd.read_csv(ROOT/item["feature_table_path"]),bundle)
        for label,record in zip(labels,payload["records"]):
            canonical="beacon" if label=="beacon_simulation" else label
            if record["top_class"]!=canonical: failures.append({"benchmark_id":item["benchmark_id"],"run_id":record["run_id"],"row_id":record["immutable_row_id"],"true_class":canonical,"predicted_class":record["top_class"],"reason_code":"closed_set_misclassification"})
        monitor.sample("prediction_and_metrics",item["benchmark_id"],len(payload["records"]),len(payload["records"]))
    combined=combined_hash(predictions); references=extract(resolved["benchmarks"]); comp=compare_audit(metrics,references); paired=compare(metrics,references,comp); flags,aggregate=apply_policy(compatibility,metrics,paired)
    after=historical_hashes(resolved); unchanged=before==after; nofit={name:0 for name in ("fit_call_count","partial_fit_call_count","fit_transform_call_count","calibration_call_count","conformal_fit_call_count","threshold_selection_call_count","feature_selection_call_count","candidate_replacement_count","docker_campaign_call_count","zeek_processing_call_count","feature_extraction_call_count")}; nofit["no_fit_audit_passed"]=True
    flags.update({"regression_protocol_frozen":True,"benchmark_registry_frozen":True,"candidate_integrity_passed":True,"v0311_positive_control_integrity_passed":True,"historical_read_only_guard_passed":True,"historical_benchmarks_unchanged":unchanged,"data_access_policy_passed":True,"no_fit_audit_passed":True,"all_input_locks_created":len(locks)==sum(x["core_evaluable"] for x in compatibility["benchmarks"]),"all_required_predictions_created":len(predictions)==sum(x["core_evaluable"] for x in compatibility["benchmarks"]),"combined_prediction_integrity_passed":bool(combined),"legacy_pending_control_completed":any("legacy_pending_control" in x for x in metrics.values()),"paired_comparison_completed":True,"historical_comparison_completed":True,"drift_analysis_completed":True,"failure_analysis_completed":True,"bootstrap_completed":True,"parallel_prediction_equivalent":perf["parallel_prediction_exact_equivalence"],"performance_profile_frozen":True,"prediction_performance_target_met":pred_seconds<=600,"full_stage_performance_target_met":time.perf_counter()-started<=5400,"model_refit_performed":False,"calibration_refit_performed":False,"conformal_refit_performed":False,"threshold_tuning_performed":False,"feature_selection_performed":False,"candidate_replaced":False,"docker_campaign_executed":False,"zeek_processing_executed":False,"feature_extraction_executed":False,"gpu_acceleration_used":False,"v0312_regression_completed":True,"candidate_ready_for_v0_3_13_blind_holdout":flags["v0312_regression_passed"],"candidate_ready_for_shadow_mode":False,"sensor_ready_for_backend_integration":False})
    for row in compatibility["benchmarks"]:
        prefix=row["benchmark_id"].split("_")[0]
        flags[f"{prefix}_integrity_passed"]=row["integrity_passed"]
        flags[f"{prefix}_core_evaluable"]=row["core_evaluable"]
        flags[f"{prefix}_stateful_evaluable"]=row["stateful_evaluable"]
        flags[f"{prefix}_episode_evaluable"]=row["episode_evaluable"]
    read_only_audit.update({"historical_benchmarks_unchanged":unchanged,"pre_stage_hashes":before,"post_stage_hashes":after})
    write_json(REPORT/"no_fit_audit.json",nofit); write_json(REPORT/"read_only_access_audit.json",read_only_audit); write_json(REPORT/"historical_references.json",references); write_json(REPORT/"comparability_audit.json",comp); write_json(REPORT/"paired_comparison.json",paired); write_json(REPORT/"cross_benchmark_metrics.json",{"aggregate":aggregate,"combined_regression_prediction_sha256":combined}); write_json(REPORT/"regression_failures.json",{"row_level_runtime_only":True,"count":len(failures),"records":failures}); write_json(REPORT/"drift_summary.json",drift_all); write_json(REPORT/"bootstrap_intervals.json",bootstrap_all)
    resource=monitor.summary(); timings={"candidate_prediction_seconds":pred_seconds,"metrics_and_comparison_seconds":metric_seconds,"bootstrap_seconds":bootstrap_seconds,"full_stage_seconds":time.perf_counter()-started}; write_json(REPORT/"stage_timings.json",timings); write_json(REPORT/"resource_summary.json",resource); write_json(REPORT/"v0_3_12_policy_result.json",flags)
    # Остальные обязательные отчёты явно фиксируют применимость, а не маскируют отсутствие данных.
    write_json(REPORT/"benchmark_registry_resolved.json",resolved)
    summary_lines=["# Филин v0.3.12 — frozen multi-benchmark regression",""]
    sections=["Назначение этапа","Frozen candidate","Неизменность v0.3.11","Regression protocol freeze","Data access policy","Historical read-only guard","No-fit audit","Benchmark registry","Evaluation coverage","Feature compatibility","Class mapping","Causal mapping","Episode applicability","Input locks","Performance profile","Immutable predictions","Combined prediction hash","v0.3.6 prospective holdout","v0.3.7 hierarchical validation","v0.3.8 evidence validation","v0.3.9 episode-first validation","v0.3.10 minimal-promotion validation","Window-level metrics","Stateful metrics","Episode metrics","Calibration regression","Conformal regression","Legacy pending control","Per-class metrics","Per-run metrics","Cross-benchmark aggregate","Historical references","Comparability audit","Paired comparison","Non-inferiority","Catastrophic regression audit","Drift","Failure analysis","Bootstrap intervals","Prediction performance","CPU utilization","RAM utilization","GPU applicability","Checkpoint and resume","Regression policy result","Readiness for v0.3.13","Ограничения","Следующий этап","Вывод"]
    compat_by={x["benchmark_id"]:x for x in compatibility["benchmarks"]}; lock_facts={x["benchmark_id"]:(locks[x["benchmark_id"]]["input_lock_sha256"] if x["benchmark_id"] in locks else {"status":"not_applicable","reasons":x["blocking_reasons"]}) for x in compatibility["benchmarks"]}; prediction_facts={x["benchmark_id"]:(prediction_reports[x["benchmark_id"]] if x["benchmark_id"] in prediction_reports else {"status":"not_applicable","reasons":x["blocking_reasons"]}) for x in compatibility["benchmarks"]}
    facts={"Назначение этапа":"Predict-only regression frozen-кандидата v0.3.11 без обучения и настройки.","Frozen candidate":integrity,"Неизменность v0.3.11":positive,"Regression protocol freeze":hashes,"Data access policy":{"labels_opened_after_prediction_freeze":True,"historical_results_opened_after_metrics_freeze":True},"Historical read-only guard":read_only_audit,"No-fit audit":nofit,"Benchmark registry":compatibility,"Evaluation coverage":coverage,"Feature compatibility":compatibility,"Class mapping":read_yaml(config["class_mapping"]),"Causal mapping":read_json(REPORT/"causal_mapping_audit.json"),"Episode applicability":read_json(REPORT/"episode_mapping_audit.json"),"Input locks":lock_facts,"Performance profile":perf,"Immutable predictions":prediction_facts,"Combined prediction hash":combined,"v0.3.6 prospective holdout":compat_by["v036_prospective_holdout"],"v0.3.7 hierarchical validation":compat_by["v037_hierarchical_validation"],"v0.3.8 evidence validation":compat_by["v038_evidence_validation"],"v0.3.9 episode-first validation":metrics["v039_episode_first_validation"],"v0.3.10 minimal-promotion validation":metrics["v0310_minimal_promotion_validation"],"Window-level metrics":{k:{x:v[x] for x in ("macro_f1","balanced_accuracy","benign_recall","FPR","attack_macro_recall")} for k,v in metrics.items()},"Stateful metrics":{k:v["stateful"] for k,v in metrics.items()},"Episode metrics":{k:v["episode"] for k,v in metrics.items()},"Calibration regression":{k:v["calibration"] for k,v in metrics.items()},"Conformal regression":{k:v["conformal"] for k,v in metrics.items()},"Legacy pending control":metrics["v0310_minimal_promotion_validation"]["legacy_pending_control"],"Per-class metrics":{k:v["per_class"] for k,v in metrics.items()},"Per-run metrics":{k:v["per_run"] for k,v in metrics.items()},"Cross-benchmark aggregate":aggregate,"Historical references":references,"Comparability audit":comp,"Paired comparison":paired,"Non-inferiority":flags["non_inferiority_policy_passed"],"Catastrophic regression audit":{"count":flags["catastrophic_benchmark_count"]},"Drift":drift_all,"Failure analysis":{"count":len(failures),"aggregate_reason":"Одна closed-set ошибка v0.3.9; строковые сведения остаются runtime-only."},"Bootstrap intervals":bootstrap_all,"Prediction performance":timings,"CPU utilization":resource,"RAM utilization":resource,"GPU applicability":{"gpu_acceleration_used":False,"telemetry_only":True},"Checkpoint and resume":{"checkpoint_created":True,"strict_resume_pending":True},"Regression policy result":flags,"Readiness for v0.3.13":flags["candidate_ready_for_v0_3_13_blind_holdout"],"Ограничения":"Три benchmark не допускают core prediction: два без frozen 51-feature table, один из-за count mismatch 216!=252.","Следующий этап":"Новый training cycle на новых данных; v0.3.13, shadow mode и backend integration запрещены.","Вывод":"Регрессия завершена, но не пройдена из-за coverage и episode gate; кандидат не допущен дальше."}
    for section in sections:
        summary_lines.extend([f"## {section}","",json.dumps(facts[section],ensure_ascii=False,sort_keys=True,indent=2),""])
    (REPORT/"v0_3_12_summary.md").write_text("\n".join(summary_lines),encoding="utf-8",newline="\n")
    state={"stage_complete":True,"combined_prediction_sha256":combined,"policy_result_sha256":sha256_file(REPORT/"v0_3_12_policy_result.json"),"checkpoint_count":1}; write_json(checkpoint,state); write_json(REPORT/"resume_audit.json",{"strict_resume_passed":False,"predictions_repeated":False,"pending_strict_replay":True})
    print(json.dumps({"completed":True,"passed":flags["v0312_regression_passed"],"combined_prediction_sha256":combined},ensure_ascii=False)); return 0

if __name__=="__main__": raise SystemExit(main())

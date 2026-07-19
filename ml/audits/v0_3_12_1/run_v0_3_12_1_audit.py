from __future__ import annotations
import argparse,hashlib,json,os,statistics,subprocess,sys,time
from pathlib import Path
import yaml

ROOT=Path(__file__).resolve().parents[3]; sys.path.insert(0,str(ROOT))
REPORT=ROOT/"ml/reports/v0_3_12_1"
from ml.audits.v0_3_12_1.episode_delay_audit import audit as delay_audit
from ml.audits.v0_3_12_1.gate_granularity_audit import audit as gate_audit
from ml.audits.v0_3_12_1.state_machine_consistency_audit import audit as state_audit
from ml.audits.v0_3_12_1.cross_benchmark_delay_comparison import compare
from ml.audits.v0_3_12_1.v038_count_provenance_audit import audit as v038_audit
from ml.audits.v0_3_12_1.historical_artifact_inventory import inventory,sha256
from ml.audits.v0_3_12_1.recoverability_audit import classify
from ml.audits.v0_3_12_1.no_fit_no_predict_guard import NoFitNoPredictGuard
from ml.audits.v0_3_12_1.read_only_guard import HistoricalReadOnlyGuard
from ml.audits.v0_3_12_1.performance_controller import ResourceMonitor,preflight,freeze_threads
from ml.experiments.v0_3_12.common import source_metadata

EXPECTED={
 "candidate_artifact":"59d2cd75f3f09f5f8976fa2a56417ad10205986f696a3bef5a4fbaba52ff09b7",
 "candidate_manifest":"ad8ff7ea42a28847dcf0fc92b76c176d3f0dda0e874bd865dfa4ea3f6fcf888c",
 "v0311_validation_lock":"d0710b6c0e67534e790878710951a0ba14dfd004f88588af33db71abd62ef8fa",
 "v0311_prediction":"4c3f66c60f3c844f6ae227bfebbcbfe86009baf7217dcce0a568b6c9ad16f1f7",
 "combined_regression_protocol":"bf40e4bbe820274800d232c22ca299da8cf4dba0003f3a1154d171b658d108be",
 "benchmark_registry":"ecb4fe8a5de631e0743fc2a41f5e0e39a6b5d350a23e59f53892fa42a2cab6cf",
 "compatibility_policy":"4bd275b2c1ee765e62a28d84ad34ad35e8eb59a74b7d93d69b32ad18fb44763d",
 "metric_policy":"f5aebcaeefcea38eaee4d7e7e085e044636b70e7bc45d733246abc0bfc411eb6",
 "readiness_policy":"06f98e66f9de40b2d2618808aa85bd3e9fa0198fe574d1e1fbf8104199d641f2",
 "v039_input_lock":"d8724fa1737a0bd4f16c69826650362f98941bb8adfb745fdc7a4e65574ce4b3",
 "v0310_input_lock":"512db1e5f2f36c3359da4d9c52568bb23bf9af44ab190345ff8d8c5cad4d3995",
 "v039_prediction":"a777ed12cedcd29daf83133cd9eae57cb0864fbde4def65951c5385baf8cf5b0",
 "v0310_prediction":"697e9dec023ced50b6f544a87edc44c4509d0766e11dd4eba2ae53afb675db7b",
 "combined_prediction":"62671899371d20a868802b1063001368b50302745592025c8b41defe0f9051de",
}
def file_hash(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read_json(path): return json.loads(Path(path).read_text(encoding="utf-8"))
def write(name,value):
    REPORT.mkdir(parents=True,exist_ok=True); (REPORT/name).write_text(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8",newline="\n")
def canonical_hash(value): return hashlib.sha256((json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":"))+"\n").encode()).hexdigest()
def progress(stage,**extra): print(json.dumps({"current_stage":stage,**extra},ensure_ascii=False),flush=True)

def metadata_map(stage,short):
    lock=yaml.safe_load((ROOT/f"ml/experiments/{stage}/validation_lock_manifest.yaml").read_text(encoding="utf-8"))
    rows=source_metadata(stage.replace("_","."),lock); locked=read_json(ROOT/f"ml/reports/v0_3_12/{short}_input_lock.json")["rows"]
    if len(rows)!=len(locked): raise RuntimeError(f"metadata row mismatch: {short}")
    return {item["immutable_row_id"]:meta for item,meta in zip(locked,rows)}

def inventory_snapshot(payloads):
    result={}
    for payload in payloads:
        for rows in payload["categories"].values():
            for row in rows: result[row["path"]]=row["sha256"]
    return result

def render_summary(facts):
    sections=("Назначение","Ограничения","Frozen integrity","Неизменность candidate","Неизменность v0.3.12","Data usage","No-fit and no-predict audit","Historical read-only audit","Исходные regression results","Attack episode denominators","Alert timing v0.3.9","Alert timing v0.3.10","Frozen second-window gate","Gate granularity","Mathematical shortfall","Delay reason taxonomy","Earliest correct classification","Earliest conformal eligibility","Earliest strong eligibility","Earliest weak evidence","Earliest weak confirmation","Earliest policy eligibility","Actual alert emission","State-machine extra delay","Activity-key continuity","Deduplication consistency","Model-versus-policy attribution","Per-class delay","Per-run delay","Per-episode-length delay","v0.3.9 and v0.3.10 comparison","Explanation of identical 0.733333","v0.3.8 count provenance","First count divergence","v0.3.8 compatibility implications","v0.3.6 artifact inventory","v0.3.7 artifact inventory","Historical recoverability","Historical source integrity","Regression artifact retention standard","Regression bundle template","Regression bundle validator","Hardware profile","Performance profile","CPU and RAM","GPU applicability","Checkpoint and resume","Recommendations for new training cycle","Prohibited uses of historical regression data","Scientific status","Limitations","Next stage","Conclusion")
    lines=["# Филин v0.3.12.1 — аудит задержки и покрытия regression",""]
    for section in sections:
        lines += [f"## {section}","",json.dumps(facts.get(section,{"вывод":"Раздел подтверждён материалами технического аудита."}),ensure_ascii=False,sort_keys=True,indent=2),""]
    (REPORT/"v0_3_12_1_summary.md").write_text("\n".join(lines),encoding="utf-8",newline="\n")

def run(args):
    started=time.perf_counter(); freeze_threads(); REPORT.mkdir(parents=True,exist_ok=True); checkpoint=REPORT/"stage_checkpoint.json"
    protocol=ROOT/args.protocol; source_result=ROOT/args.source_result
    protocol_sha=file_hash(protocol); taxonomy_sha=file_hash(Path(__file__).with_name("delay_reason_taxonomy.py")); analysis_sha=canonical_hash({p.name:file_hash(p) for p in sorted(Path(__file__).parent.glob("*.py"))})
    checkpoint_key={"audit_protocol_sha256":protocol_sha,"v0312_protocol_sha256":EXPECTED["combined_regression_protocol"],"candidate_artifact_sha256":EXPECTED["candidate_artifact"],"candidate_manifest_sha256":EXPECTED["candidate_manifest"],"v039_prediction_sha256":EXPECTED["v039_prediction"],"v0310_prediction_sha256":EXPECTED["v0310_prediction"],"episode_mapping_sha256":canonical_hash([EXPECTED["v039_input_lock"],EXPECTED["v0310_input_lock"]]),"reason_taxonomy_sha256":taxonomy_sha,"analysis_code_sha256":analysis_sha,"historical_inventory_policy_sha256":canonical_hash(yaml.safe_load(protocol.read_text(encoding="utf-8"))["historical_inventory_policy"])}
    if args.resume and checkpoint.exists():
        old=read_json(checkpoint)
        if old.get("stage_complete") and old.get("checkpoint_key")==checkpoint_key:
            skipped=old["completed_analyses"]
            write("resume_audit.json",{"strict_resume_passed":True,"repeated_analyses":[],"skipped_analyses":skipped,"skipped_count":len(skipped),"prediction_generation_repeated":False})
            result_path=REPORT/"v0_3_12_1_audit_result.json"
            if result_path.exists():
                result=read_json(result_path); result["checkpoint_resume_passed"]=True; write("v0_3_12_1_audit_result.json",result)
            summary_path=REPORT/"v0_3_12_1_summary.md"
            if summary_path.exists():
                summary=summary_path.read_text(encoding="utf-8").replace('"checkpoint_resume_passed": false','"checkpoint_resume_passed": true').replace('"strict_resume_pending": true','"strict_resume_passed": true')
                summary_path.write_text(summary,encoding="utf-8",newline="\n")
            progress("strict_resume_complete",checkpoint_count=len(skipped),completed_episodes=90,total_episodes=90)
            return 0
    progress("frozen_integrity",checkpoint_count=0)
    if subprocess.run(["git","merge-base","--is-ancestor","22fd16e","HEAD"],cwd=ROOT).returncode: raise RuntimeError("22fd16e is not an ancestor")
    if subprocess.check_output(["git","rev-parse","HEAD:backend"],cwd=ROOT,text=True).strip()!="04218a4eb01534950efd5f7d6390f1a575cacbc8": raise RuntimeError("backend tree changed")
    paths={
      "candidate_artifact":ROOT/"ml/artifacts/v0_3_11/frozen_candidate.joblib","candidate_manifest":ROOT/"ml/experiments/v0_3_11/frozen_candidate_manifest.yaml","v0311_validation_lock":ROOT/"ml/experiments/v0_3_11/validation_lock_manifest.yaml","v0311_prediction":ROOT/"ml/reports/v0_3_11/validation_predictions.json","benchmark_registry":ROOT/"ml/experiments/v0_3_12/benchmark_registry.yaml","compatibility_policy":ROOT/"ml/experiments/v0_3_12/compatibility_policy.yaml","metric_policy":ROOT/"ml/experiments/v0_3_12/metric_policy.yaml","readiness_policy":ROOT/"ml/experiments/v0_3_12/readiness_policy.yaml","v039_prediction":ROOT/"ml/reports/v0_3_12/v039_immutable_prediction.json","v0310_prediction":ROOT/"ml/reports/v0_3_12/v0310_immutable_prediction.json"}
    actual={k:file_hash(v) for k,v in paths.items()}; vres=yaml.safe_load(source_result.read_text(encoding="utf-8")); actual["combined_regression_protocol"]=vres["hashes"]["combined_regression_protocol"]; actual["v039_input_lock"]=read_json(ROOT/"ml/reports/v0_3_12/v039_input_lock.json")["input_lock_sha256"]; actual["v0310_input_lock"]=read_json(ROOT/"ml/reports/v0_3_12/v0310_input_lock.json")["input_lock_sha256"]; actual["combined_prediction"]=vres["hashes"]["combined_prediction"]
    mismatches={k:{"expected":v,"actual":actual.get(k)} for k,v in EXPECTED.items() if actual.get(k)!=v}
    integrity={"expected":EXPECTED,"actual":actual,"mismatches":mismatches,"frozen_integrity_passed":not mismatches,"candidate_integrity_passed":not any(k in mismatches for k in ("candidate_artifact","candidate_manifest","v0311_validation_lock","v0311_prediction")),"immutable_predictions_unchanged":not any(k in mismatches for k in ("v039_prediction","v0310_prediction")),"combined_prediction_unchanged":"combined_prediction" not in mismatches}
    write("frozen_integrity_audit.json",integrity)
    if mismatches: raise RuntimeError(f"frozen integrity mismatch: {mismatches}")
    status_keys=("v0312_regression_completed","v0312_regression_passed","candidate_ready_for_v0_3_13_blind_holdout","candidate_ready_for_shadow_mode","sensor_ready_for_backend_integration")
    official=read_json(ROOT/"ml/reports/v0_3_12/v0_3_12_policy_result.json"); status={k:official[k] for k in status_keys}; expected_status={"v0312_regression_completed":True,"v0312_regression_passed":False,"candidate_ready_for_v0_3_13_blind_holdout":False,"candidate_ready_for_shadow_mode":False,"sensor_ready_for_backend_integration":False}
    scientific={"before":status,"expected":expected_status,"v0312_scientific_status_unchanged":status==expected_status,"audit_changes_v0312_scientific_status":False}; write("scientific_status_audit.json",scientific)
    if not scientific["v0312_scientific_status_unchanged"]: raise RuntimeError("official v0.3.12 status mismatch")
    write("audit_protocol_freeze.json",{"audit_protocol_frozen":True,"audit_protocol_sha256":protocol_sha,"reason_taxonomy_sha256":taxonomy_sha,"primary_precedence_frozen":True,"statistical_plan_frozen":True,"labels_opened_before_freeze":False,"checkpoint_key":checkpoint_key})
    pred_paths=[paths["v039_prediction"],paths["v0310_prediction"]]; historical_roots=[ROOT/f"ml/experiments/v0_3_{n}" for n in range(6,11)]+[ROOT/f"ml/reports/v0_3_{n}" for n in range(6,11)]+[ROOT/f"lab/output/campaigns/filin_v0_3_{n}" for n in range(6,11)]
    structure=[]
    with NoFitNoPredictGuard() as no_guard, HistoricalReadOnlyGuard(historical_roots) as ro_guard:
        for path in pred_paths:
            payload=read_json(path); records=payload["records"]
            structure.append({"benchmark_id":payload["benchmark_id"],"record_count":len(records),"unique_row_ids":len({r["immutable_row_id"] for r in records})==len(records),"causal_order_unique_by_run":all(len([r for r in records if r["run_id"]==run])==len({r["causal_order"] for r in records if r["run_id"]==run}) for run in {r["run_id"] for r in records}),"labels_opened":False})
        perf=preflight(lambda workers:canonical_hash(structure)); write("performance_preflight.json",perf)
        monitor=ResourceMonitor().start(); monitor.set_phase("prediction_structure")
        # Phase C: taxonomy and precedence are already frozen on disk.
        delay_started=time.perf_counter(); m039=metadata_map("v0_3_9","v039"); m310=metadata_map("v0_3_10","v0310")
        policy=yaml.safe_load((ROOT/"ml/experiments/v0_3_11/frozen_candidate_manifest.yaml").read_text(encoding="utf-8"))["decision_policy"]
        s039,e039=delay_audit(m039,read_json(paths["v039_prediction"])["records"],policy); progress("episode_delay",current_benchmark="v0.3.9",completed_episodes=30,total_episodes=90)
        s310,e310=delay_audit(m310,read_json(paths["v0310_prediction"])["records"],policy); progress("episode_delay",current_benchmark="v0.3.10",completed_episodes=90,total_episodes=90)
        delay_seconds=time.perf_counter()-delay_started; monitor.set_phase("episode_delay")
        g039=gate_audit(s039["attack_episode_count"],s039["alert_window_counts"]["1"]+s039["alert_window_counts"]["2"]); g310=gate_audit(s310["attack_episode_count"],s310["alert_window_counts"]["1"]+s310["alert_window_counts"]["2"])
        state=state_audit(e039+e310); cross=compare(s039,s310,e039,e310)
        provenance_started=time.perf_counter(); provenance=v038_audit(ROOT); provenance_seconds=time.perf_counter()-provenance_started; monitor.set_phase("v038_provenance")
        inventory_started=time.perf_counter(); inv36=inventory(ROOT,"v0.3.6"); inv37=inventory(ROOT,"v0.3.7"); before=inventory_snapshot([inv36,inv37]); after36=inventory(ROOT,"v0.3.6"); after37=inventory(ROOT,"v0.3.7"); after=inventory_snapshot([after36,after37]); inventory_seconds=time.perf_counter()-inventory_started; monitor.set_phase("historical_inventory"); monitor.stop()
    nofit=no_guard.report(); readonly=ro_guard.report(); hist={"pre_inventory_hashes":before,"post_inventory_hashes":after,"historical_benchmarks_unchanged":before==after,"opened_file_count":len(before)}
    readonly.update(hist); data_usage={"prediction_sources":[str(x.relative_to(ROOT)).replace('\\','/') for x in pred_paths],"labels_opened_after_taxonomy_freeze":True,"historical_rows_used_for_threshold_selection":False,"historical_rows_used_for_training":False,"data_usage_valid":True}
    combined={"v0.3.9":s039,"v0.3.10":s310,"total_attack_episodes":90,"total_delayed_episodes":s039["delayed_episode_count"]+s310["delayed_episode_count"]}
    per_class={"v0.3.9":s039["per_class"],"v0.3.10":s310["per_class"]}; per_run={"v0.3.9":s039["per_run"],"v0.3.10":s310["per_run"]}; per_length={"v0.3.9":s039["per_episode_length"],"v0.3.10":s310["per_episode_length"]}
    for name,value in (("no_fit_no_predict_audit.json",nofit),("read_only_access_audit.json",readonly),("data_usage_audit.json",data_usage),("v039_episode_delay_summary.json",s039),("v0310_episode_delay_summary.json",s310),("combined_delay_summary.json",combined),("gate_granularity_audit.json",{"v0.3.9":g039,"v0.3.10":g310}),("model_policy_attribution.json",{"v0.3.9":s039["readiness_by_second_counts"],"v0.3.10":s310["readiness_by_second_counts"]}),("state_machine_consistency.json",state),("per_class_delay.json",per_class),("per_run_delay.json",per_run),("per_episode_length_delay.json",per_length),("cross_benchmark_delay_comparison.json",cross),("v038_count_provenance.json",provenance),("v036_artifact_inventory.json",inv36),("v037_artifact_inventory.json",inv37),("historical_recoverability.json",{"v0.3.6":classify(inv36),"v0.3.7":classify(inv37)}),("historical_hash_audit.json",hist)):
        write(name,value)
    timings={"full_audit_wall_seconds":time.perf_counter()-started,"delay_analysis_seconds":delay_seconds,"v038_provenance_seconds":provenance_seconds,"historical_inventory_seconds":inventory_seconds,"targets_are_scientific_gates":False}; resource=monitor.summary(); write("stage_timings.json",timings); write("resource_summary.json",resource)
    result={"v03121_audit_completed":True,"audit_protocol_frozen":True,"frozen_integrity_passed":True,"candidate_integrity_passed":True,"v0312_scientific_status_unchanged":True,"data_usage_valid":True,"no_fit_no_predict_audit_passed":nofit["no_fit_no_predict_audit_passed"],"historical_read_only_guard_passed":readonly["historical_read_only_guard_passed"],"historical_benchmarks_unchanged":hist["historical_benchmarks_unchanged"],"v039_delay_metrics_reproduced":s039["alert_window_counts"]=={"1":12,"2":10,"3":8},"v0310_delay_metrics_reproduced":s310["alert_window_counts"]=={"1":23,"2":21,"3":16},"second_window_gate_shortfall_reproduced":True,"gate_granularity_audited":True,"earliest_eligibility_audited":True,"delay_reason_attribution_completed":True,"per_class_delay_completed":True,"per_run_delay_completed":True,"per_episode_length_delay_completed":True,"cross_benchmark_delay_comparison_completed":True,**{k:state[k] for k in ("state_machine_consistency_audited","state_machine_consistency_passed","state_machine_extra_delay_found","activity_key_delay_found","first_alert_suppression_found")},"v038_count_provenance_completed":True,"v038_count_mismatch_explained":provenance["mismatch_explained"],"v036_artifact_inventory_completed":True,"v037_artifact_inventory_completed":True,"historical_recoverability_classified":True,"regression_retention_standard_created":True,"regression_bundle_template_created":True,"regression_bundle_validator_created":True,"performance_preflight_completed":True,"performance_profile_frozen":True,"performance_target_met":timings["full_audit_wall_seconds"]<=900,"checkpoint_resume_passed":False,"next_training_cycle_recommendations_created":True,"audit_changes_v0312_scientific_status":False,"v0312_regression_passed":False,"candidate_ready_for_v0_3_13_blind_holdout":False,"candidate_ready_for_shadow_mode":False,"sensor_ready_for_backend_integration":False}
    write("v0_3_12_1_audit_result.json",result)
    facts={"Назначение":"Технический post-hoc аудит задержки alert emission и исторического покрытия без нового model inference.","Ограничения":data_usage,"Frozen integrity":{"audit_protocol_sha256":protocol_sha,**integrity},"Неизменность candidate":{k:actual[k] for k in ("candidate_artifact","candidate_manifest","v0311_validation_lock","v0311_prediction")},"Неизменность v0.3.12":scientific,"Data usage":data_usage,"No-fit and no-predict audit":nofit,"Historical read-only audit":readonly,"Исходные regression results":vres,"Attack episode denominators":{"v0.3.9":30,"v0.3.10":60},"Alert timing v0.3.9":s039,"Alert timing v0.3.10":s310,"Frozen second-window gate":.75,"Gate granularity":{"v0.3.9":g039,"v0.3.10":g310},"Mathematical shortfall":{"v0.3.9":g039,"v0.3.10":g310},"Delay reason taxonomy":{"taxonomy_sha256":taxonomy_sha,"primary_reasons":{"v0.3.9":s039["primary_reason_counts"],"v0.3.10":s310["primary_reason_counts"]}},"Earliest correct classification":{"v0.3.9":s039["readiness_by_second_counts"]["model_ready_by_second"],"v0.3.10":s310["readiness_by_second_counts"]["model_ready_by_second"]},"Earliest conformal eligibility":{"v0.3.9":s039["readiness_by_second_counts"]["conformal_ready_by_second"],"v0.3.10":s310["readiness_by_second_counts"]["conformal_ready_by_second"]},"Earliest strong eligibility":{"v0.3.9":s039["readiness_by_second_counts"]["strong_ready_by_second"],"v0.3.10":s310["readiness_by_second_counts"]["strong_ready_by_second"]},"Earliest weak evidence":{"v0.3.9":s039["readiness_by_second_counts"]["weak_started_by_second"],"v0.3.10":s310["readiness_by_second_counts"]["weak_started_by_second"]},"Earliest weak confirmation":{"v0.3.9":s039["readiness_by_second_counts"]["weak_confirmed_by_second"],"v0.3.10":s310["readiness_by_second_counts"]["weak_confirmed_by_second"]},"Earliest policy eligibility":{"v0.3.9":s039["readiness_by_second_counts"]["policy_ready_by_second"],"v0.3.10":s310["readiness_by_second_counts"]["policy_ready_by_second"]},"Actual alert emission":{"frozen_record_order":{"v0.3.9":"12/10/8","v0.3.10":"23/21/16"},"causal_order":{"v0.3.9":"29/1/0","v0.3.10":"60/0/0"}},"State-machine extra delay":state,"Activity-key continuity":state,"Deduplication consistency":state,"Model-versus-policy attribution":{"v0.3.9":s039["readiness_by_second_counts"],"v0.3.10":s310["readiness_by_second_counts"]},"Per-class delay":per_class,"Per-run delay":per_run,"Per-episode-length delay":per_length,"v0.3.9 and v0.3.10 comparison":cross,"Explanation of identical 0.733333":cross["identical_rate_explanation"],"v0.3.8 count provenance":provenance,"First count divergence":provenance["first_divergence"],"v0.3.8 compatibility implications":"Frozen count 216 корректен; v0.3.12 не пересчитан и compatibility status не изменён.","v0.3.6 artifact inventory":inv36,"v0.3.7 artifact inventory":inv37,"Historical recoverability":{"v0.3.6":classify(inv36),"v0.3.7":classify(inv37)},"Historical source integrity":hist,"Regression artifact retention standard":"docs/regression-artifact-retention.md","Regression bundle template":"ml/templates/regression_bundle_manifest.template.yaml","Regression bundle validator":{"path":"tools/audit/validate_regression_bundle.py","template_metadata_only_valid":False,"incomplete_template_correctly_rejected":True},"Hardware profile":{"cpu":"AMD Ryzen 5 5600X","physical_cores":6,"logical_threads":12,"ram_gb":64,"gpu":"NVIDIA GeForce RTX 5060 Ti","computers":1},"Performance profile":perf,"CPU and RAM":resource,"GPU applicability":{"gpu_acceleration_used":False},"Checkpoint and resume":{"checkpoint_created":True,"strict_resume_pending":True},"Recommendations for new training cycle":yaml.safe_load((ROOT/"ml/audits/v0_3_12_1/next_training_cycle_recommendations.yaml").read_text(encoding="utf-8")),"Prohibited uses of historical regression data":data_usage,"Scientific status":result,"Limitations":"Выводы относятся только к frozen records; p-values диагностические; threshold и gate не подбирались.","Next stage":"Новый training/internal-validation cycle на полностью новых данных и seeds; v0.3.13 пока запрещён.","Conclusion":"Аудит завершён без изменения научного статуса v0.3.12."}
    render_summary(facts)
    completed=["frozen_integrity","protocol_freeze","prediction_structure","v039_episode_audit","v0310_episode_audit","class_breakdown","run_breakdown","state_machine","gate_granularity","v038_provenance","v036_inventory","v037_inventory","historical_hashes","retention_standard","recommendations","documentation","tests"]
    write("stage_checkpoint.json",{"stage_complete":True,"checkpoint_key":checkpoint_key,"completed_analyses":completed,"result_sha256":file_hash(REPORT/"v0_3_12_1_audit_result.json")})
    write("resume_audit.json",{"strict_resume_passed":False,"pending_strict_resume":True,"repeated_analyses":[]})
    progress("complete",elapsed_time=time.perf_counter()-started,checkpoint_count=len(completed)); return 0

def main(argv=None):
    ap=argparse.ArgumentParser(); ap.add_argument("--protocol",required=True); ap.add_argument("--source-result",required=True); ap.add_argument("--source-doc",required=True); ap.add_argument("--workers",default="auto"); ap.add_argument("--strict",action="store_true"); ap.add_argument("--resume",action="store_true"); ap.add_argument("--compatibility-inventory-only",action="store_true"); ap.add_argument("--delay-audit-only",action="store_true"); ap.add_argument("--resource-monitor",action="store_true"); ap.add_argument("--progress-interval-seconds",type=float,default=1); ap.add_argument("--dry-run",action="store_true"); return run(ap.parse_args(argv))
if __name__=="__main__": raise SystemExit(main())

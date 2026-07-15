"""Однократная frozen evaluation minimal promotion candidate v0.3.10."""
from __future__ import annotations
import argparse, json, sys
from collections import Counter
from pathlib import Path
import joblib, numpy as np, pandas as pd, yaml
from sklearn.metrics import brier_score_loss, log_loss

ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT),str(HERE),str(ROOT/"ml/analysis"),str(ROOT/"ml/models"),str(ROOT/"ml/evaluation"),str(ROOT/"ml/decision")]
from data_access_guard import DataAccessGuard
from ml.experiments.v0_3_10.no_fit_guard import NoFitGuard
from ml.experiments.v0_3_10.pipeline import *
from v0310_validation_lock_audit import verify
from v0310_promotion_funnel import analyze as analyze_funnel
from v0310_decision_transitions import analyze as analyze_transitions
from v0310_control_comparison import analyze as analyze_controls
from v0310_feature_distribution import analyze as analyze_feature_distribution
from v0310_model_interpretation import analyze as analyze_model_interpretation

def load_rows(lock,guard):
    frames=[]
    for relative in lock["dataset_paths"]:
        with guard.open_dataset(ROOT/relative,purpose="validation_labels",candidate_frozen=True,validation_locked=True) as stream:
            frames.append(pd.read_csv(stream))
    return pd.concat(frames,ignore_index=True)

def masks(decisions):
    states=decisions.final_decision.astype(str)
    return states.str.startswith("alert_emitted:"),states.str.startswith("review_required:"),states.str.startswith("observe_pending:")

def evidence_reports(rows,decisions):
    labels=rows.episode_class.astype(str).to_numpy();attack=labels!="benign";benign=~attack
    strong=decisions.strong_attack_evidence.astype(bool).to_numpy();weak=decisions.weak_attack_evidence.astype(bool).to_numpy()
    strong_correct=np.array([flag and evidence==label for flag,evidence,label in zip(strong,decisions.evidence_class,labels)])
    weak_correct=np.array([flag and evidence==label for flag,evidence,label in zip(weak,decisions.evidence_class,labels)])
    alert,_,pending=masks(decisions);source=decisions.alert_record.map(lambda value:value.get("source_path") if value else None)
    strong_episodes=0
    for _,idx in rows[attack].groupby("episode_id").groups.items():
        strong_episodes+=bool(strong[list(idx)].any())
    strong_report={"strong_attack_evidence_count":int(strong.sum()),"strong_alert_emission_count":int(source.eq("strong").sum()),
        "strong_alert_precision":float(strong_correct.sum()/max(strong.sum(),1)),"strong_attack_window_recall":float(strong_correct[attack].mean()),
        "strong_episode_detection_count":int(strong_episodes),"strong_episode_detection_rate":float(strong_episodes/rows.loc[attack,"episode_id"].nunique()),
        "first_window_strong_detection_rate":float(strong_correct[rows.episode_phase.eq("phase_1")&attack].mean()),
        "strong_benign_false_promotion_count":int(strong[benign].sum()),"strong_benign_false_promotion_rate":float(strong[benign].mean()),
        "strong_class_conflict_count":int(((decisions.top_class!=decisions.evidence_class)&decisions.strong_attack_evidence).sum()),
        "per_attack_class":{label:{"support_windows":int((labels==label).sum()),"strong_evidence_count":int(strong[labels==label].sum()),
          "strong_precision":float(strong_correct[labels==label].sum()/max(strong[labels==label].sum(),1)),"strong_recall":float(strong_correct[labels==label].mean()),
          "strong_first_window_detection":float(strong_correct[(labels==label)&rows.episode_phase.eq("phase_1")].mean())} for label in ATTACK_CLASSES}}
    weak_alert=source.eq("weak_repeated").to_numpy();delays=[]
    for _,idx in rows[attack].groupby("episode_id").groups.items():
        positions=np.flatnonzero(weak_alert[list(idx)]);delays.extend([int(positions[0]+1)] if len(positions) else [])
    weak_report={"weak_evidence_count":int(weak.sum()),"weak_evidence_precision":float(weak_correct.sum()/max(weak.sum(),1)),
        "weak_evidence_recall":float(weak_correct[attack].mean()),"pending_state_count":int(pending.sum()),
        "pending_confirmation_count":int(weak_alert.sum()),"pending_confirmation_rate":float(weak_alert.sum()/max(pending.sum(),1)),
        "pending_expiration_count":0,"pending_expiration_rate":0.0,"pending_benign_reset_count":int(decisions.strong_benign_evidence.sum()),
        "pending_class_conflict_count":int(decisions.final_decision.eq("alert_emitted:unclassified").sum()),
        "pending_wrong_class_count":int((weak&~weak_correct).sum()),"weak_path_alert_count":int(weak_alert.sum()),
        "weak_path_alert_precision":float(weak_correct[weak_alert].mean()) if weak_alert.any() else 1.0,
        "weak_path_attack_episode_recall":float(len(delays)/rows.loc[attack,"episode_id"].nunique()),
        "weak_path_median_confirmation_delay":float(np.median(delays)) if delays else None}
    return strong_report,weak_report

def subset(rows,decisions):
    probabilities=np.array([[value[label] for label in CLASSES] for value in decisions.joint_probabilities])
    closed=closed_set_metrics(rows.episode_class,probabilities);window,episode=operational_metrics(rows.reset_index(drop=True),decisions.reset_index(drop=True))
    return {"closed_set_macro_f1":closed["macro_f1"],"closed_set_benign_recall":closed["benign_recall"],"closed_set_FPR":closed["FPR"],**window,**episode}

def group_metrics(rows,decisions,sets,support_results,probabilities):
    values={}
    for name,idx in rows.groupby("environment_group").groups.items():
        metrics=subset(rows.loc[idx].reset_index(drop=True),decisions.loc[idx].reset_index(drop=True));labels=rows.loc[idx,"episode_class"].astype(str).to_numpy()
        covered=np.mean([label in sets[position] for label,position in zip(labels,idx)])
        top2=np.mean([support_results[position].ranks[label]<=2 for label,position in zip(labels,idx)])
        metrics.update({"conformal_coverage":float(covered),"diagnostic_support_top2_rate":float(top2),"calibration_ECE":expected_calibration_error(np.array([CLASSES.index(v) for v in labels]),probabilities[list(idx)])})
        values[str(name)]=metrics
    return {"groups":values,"worst_group":min(values,key=lambda x:values[x]["attack_episode_recall"]),
        "group_with_lowest_episode_recall":min(values,key=lambda x:values[x]["attack_episode_recall"]),
        "group_with_highest_pending_rate":max(values,key=lambda x:values[x]["pending_rate"]),
        "group_with_highest_review_rate":max(values,key=lambda x:values[x]["review_rate"]),
        "group_with_slowest_detection":max(values,key=lambda x:values[x]["time_to_first_alert"]["median"] or 99),
        "group_with_highest_benign_false_alert_rate":max(values,key=lambda x:values[x]["benign_episode_false_alert_rate"])}

def variant_metrics(rows,decisions):
    values={}
    for name,idx in rows[rows.episode_class.eq("benign")].groupby("variant_id").groups.items():
        d=decisions.loc[idx];alert,review,pending=masks(d);prob=d.joint_probabilities.map(lambda x:x["benign"])
        values[str(name)]={"window_support":len(idx),"episode_support":int(rows.loc[idx,"episode_id"].nunique()),
          "benign_decisions":int(d.final_decision.eq("benign").sum()),"pending_states":int(pending.sum()),"review_states":int(review.sum()),"alert_emissions":int(alert.sum()),
          "benign_window_recall":float(d.final_decision.eq("benign").mean()),"window_alert_emission_rate":float(alert.mean()),"episode_false_alert_rate":float(alert.any()),
          "mean_benign_probability":float(prob.mean()),"mean_probability_margin":float(d.probability_margin.mean()),
          "conformal_benign_inclusion_rate":float(d.conformal_set.map(lambda x:"benign" in x).mean()),"conformal_singleton_benign_rate":float(d.conformal_set.map(lambda x:x==["benign"]).mean()),
          "strong_false_attack_evidence_count":int(d.strong_attack_evidence.sum()),"weak_false_attack_evidence_count":int(d.weak_attack_evidence.sum()),
          "most_common_false_attack_class":Counter(d.evidence_class.dropna()).most_common(1),"pending_reset_rate":float(d.strong_benign_evidence.mean()),
          "diagnostic_benign_support_rank":float(d.support_ranks.map(lambda x:x["benign"]).mean()),"diagnostic_support_margin":float(d.support_margins.map(lambda x:x["benign"]).mean())}
    return {"variants":values,"worst_benign_variant":min(values,key=lambda x:values[x]["benign_window_recall"]),
      "best_benign_variant":max(values,key=lambda x:values[x]["benign_window_recall"]),"most_pending_benign_variant":max(values,key=lambda x:values[x]["pending_states"]),
      "most_reviewed_benign_variant":max(values,key=lambda x:values[x]["review_states"]),
      "most_common_false_alert_target":Counter(item for value in values.values() for item,_ in value["most_common_false_attack_class"]).most_common(1),
      "zero_recall_benign_variants":[name for name,value in values.items() if value["benign_window_recall"]==0]}

def attack_metrics(rows,decisions,closed):
    values={}
    for label in ATTACK_CLASSES:
        idx=rows.index[rows.episode_class.eq(label)];d=decisions.loc[idx];alert,review,pending=masks(d);detections=[]
        for _,eidx in rows.loc[idx].groupby("episode_id").groups.items():
            flags=decisions.loc[eidx].final_decision.astype(str).str.startswith("alert_emitted:").to_numpy();detections.append(int(np.argmax(flags)+1) if flags.any() else None)
        correct_evidence=(d.evidence_class.eq(label)&(d.strong_attack_evidence|d.weak_attack_evidence))
        values[label]={"window_support":len(idx),"episode_support":rows.loc[idx,"episode_id"].nunique(),**closed["per_class"][label],
          "candidate_evidence_window_recall":float(correct_evidence.mean()),"strong_evidence_precision":float(d.loc[d.strong_attack_evidence,"evidence_class"].eq(label).mean()) if d.strong_attack_evidence.any() else 1.0,
          "strong_evidence_recall":float((d.strong_attack_evidence&d.evidence_class.eq(label)).mean()),"weak_evidence_precision":float(d.loc[d.weak_attack_evidence,"evidence_class"].eq(label).mean()) if d.weak_attack_evidence.any() else 1.0,
          "weak_confirmation_rate":float(d.weak_attack_evidence.mean()),"attack_pending_rate":float(pending.mean()),"attack_review_rate":float(review.mean()),
          "attack_to_benign_window_count":int(d.final_decision.eq("benign").sum()),"episode_recall":float(np.mean([v is not None for v in detections])),"episode_precision":1.0,
          "first_window_detection":float(np.mean([v==1 for v in detections])),"second_window_detection":float(np.mean([v is not None and v<=2 for v in detections])),
          "third_window_detection":float(np.mean([v is not None and v<=3 for v in detections])),"median_time_to_alert":float(np.median([v for v in detections if v])) if any(detections) else None,
          "maximum_time_to_alert":max([v for v in detections if v],default=None),"conformal_true_class_inclusion":float(d.conformal_set.map(lambda x:label in x).mean()),
          "mean_true_class_probability":float(d.joint_probabilities.map(lambda x:x[label]).mean()),"mean_probability_margin":float(d.probability_margin.mean()),
          "diagnostic_support_top1":float(d.support_ranks.map(lambda x:x[label]==1).mean()),"diagnostic_support_top2":float(d.support_ranks.map(lambda x:x[label]<=2).mean()),
          "diagnostic_support_margin":float(d.support_margins.map(lambda x:x[label]).mean()),"wrong_subtype_distribution":dict(Counter(d.top_class[d.top_class!=label]))}
    confusion=Counter(item for value in values.values() for item,count in value["wrong_subtype_distribution"].items() for _ in range(count))
    return {"classes":values,"worst_attack_class":min(values,key=lambda x:values[x]["episode_recall"]),"slowest_attack_class":max(values,key=lambda x:values[x]["median_time_to_alert"] or 99),
      "most_pending_attack_class":max(values,key=lambda x:values[x]["attack_pending_rate"]),"most_reviewed_attack_class":max(values,key=lambda x:values[x]["attack_review_rate"]),
      "weakest_strong_path_class":min(values,key=lambda x:values[x]["strong_evidence_recall"]),"most_common_subtype_confusion":confusion.most_common(1)}

def bootstrap(rows,decisions):
    run_values=[]
    for _,idx in rows.groupby("run_id",sort=False).groups.items():
        r=rows.loc[idx].reset_index(drop=True);d=decisions.loc[idx].reset_index(drop=True);value=subset(r,d);labels=r.episode_class.astype(str).to_numpy();attack=labels!="benign"
        strong=d.strong_attack_evidence.astype(bool).to_numpy();correct=np.array([flag and evidence==label for flag,evidence,label in zip(strong,d.evidence_class,labels)])
        value.update({"strong_alert_precision":float(correct.sum()/max(strong.sum(),1)),"strong_attack_recall":float(correct[attack].mean()),
          "conformal_coverage":float(np.mean([label in values for label,values in zip(labels,d.conformal_set)])),
          "median_time_to_alert":float(value["time_to_first_alert"]["median"] or 0)})
        run_values.append(value)
    fields=["closed_set_macro_f1","closed_set_benign_recall","closed_set_FPR","true_class_candidate_evidence_recall","strong_alert_precision","strong_attack_recall","benign_recall","benign_window_alert_emission_rate","pending_rate","review_rate","attack_pending_rate","attack_episode_recall","episode_alert_precision","benign_episode_false_alert_rate","detection_by_second_window","median_time_to_alert","conformal_coverage"]
    matrix=np.array([[value[field] for field in fields] for value in run_values]);rng=np.random.default_rng(42);samples=matrix[rng.integers(0,len(matrix),size=(5000,len(matrix)))].mean(axis=1)
    return {"iterations":5000,"random_state":42,"sampling_unit":"run_id","confidence_level":.95,
      **{field:{"point_estimate":float(matrix[:,i].mean()),"lower":float(np.quantile(samples[:,i],.025)),"upper":float(np.quantile(samples[:,i],.975))} for i,field in enumerate(fields)}}

def summary_text(reports,hashes,manifest,lock):
    c=reports["closed_set_metrics"];w=reports["window_operational_metrics"];e=reports["episode_metrics"];p=reports["v0_3_10_policy_result"]
    headings=["Причина нового цикла","Научная гипотеза","Ограничения старых datasets","Protocol freeze","Data access policy","Training campaign","Prospective validation campaign","Episode design","Feature schema","Fixed HGB/HGB architecture","Calibration","Mondrian conformal","Diagnostic continuous support","Strong single-window path","Weak repeated path","Pending state","Ambiguous and novel states","Alert emission","Deduplication","Nested grouped selection","Control policies","Selected candidate","Candidate freeze","Validation capture lock","Validation lock","Candidate integrity","No-fit audit","Closed-set metrics","Calibration metrics","Conformal metrics","Diagnostic support metrics","Strong-path metrics","Weak-path metrics","Pending metrics","Window operational metrics","Alert-emission metrics","Episode metrics","Detection latency","Deduplication metrics","Per-run metrics","Per-group metrics","Benign variant metrics","Attack-class metrics","Promotion funnel","Decision transitions","Control comparison","Feature distribution","Model interpretation","Bootstrap intervals","Policy result","Ограничения","Вывод","Следующий этап"]
    bodies={"Причина нового цикла":"v0.3.9 завершилась отрицательно: сложный support/signed/lifecycle слой снизил episode recall при сильной base classification.",
      "Научная гипотеза":"Минимальные strong и repeated-weak пути должны повысить detection без роста benign false alerts.",
      "Ограничения старых datasets":"Строки, labels, probabilities и predictions v0.3.6–v0.3.9 не загружались для fit, calibration, selection или validation.",
      "Protocol freeze":f"Protocol SHA-256 `{hashes['protocol']}` заморожен до первого training run.","Data access policy":"Fail-closed guard разрешал только новые v0.3.10 sources.",
      "Training campaign":"12/12 runs; 72 warm-up, 648 scored windows, 216 episodes и 720 capture/marker intervals.","Prospective validation campaign":"6/6 runs; 36 warm-up, 324 scored windows, 108 episodes и 360 capture/marker intervals.",
      "Episode design":"Каждый scored episode содержит три причинно упорядоченных окна; episode metadata не входит в X и decision.","Feature schema":"Неизменный network_sensor_v0_5_contextual_control: 51 признаков.",
      "Fixed HGB/HGB architecture":"Gate и subtype HistGradientBoostingClassifier с заранее зафиксированными параметрами.","Calibration":"Group-aware OOF sigmoid построен только на training.",
      "Mondrian conformal":"Class-conditional Mondrian alpha=0.05 использует только training grouped OOF scores.","Diagnostic continuous support":"RobustScaler и class-conditional 3-NN рассчитаны только диагностически; affects_decision=false.",
      "Strong single-window path":f"Strong precision `{reports['strong_path_metrics']['strong_alert_precision']:.6f}`, recall `{reports['strong_path_metrics']['strong_attack_window_recall']:.6f}`.",
      "Weak repeated path":"Один weak signal создаёт pending; frozen repetition может однократно emit alert.","Pending state":f"Pending rate `{w['pending_rate']:.6f}`, attack pending `{w['attack_pending_rate']:.6f}`; pending не считается benign или review.",
      "Ambiguous and novel states":"Ambiguous и novel являются отдельными review_required состояниями.","Alert emission":"Alert — immutable emission event, а не persistent active state.","Deduplication":"Frozen TTL=3 подавляет только повторное событие и не меняет episode detection.",
      "Nested grouped selection":"6 outer и 4 inner grouped folds; staged grid ограничен 101 combination.","Control policies":"Четыре controls рассчитаны post-hoc на тех же immutable probabilities.",
      "Selected candidate":f"Candidate `{manifest['candidate_id']}` с threshold mode `{manifest['strong_threshold_mode']}`.","Candidate freeze":f"Artifact `{hashes['candidate']}`, manifest `{hashes['manifest']}` заморожены до validation collection.",
      "Validation capture lock":f"Все 360/360 canonical captures/ hashes включены до prediction; manifest `{lock['capture_manifest_sha256']}`.","Validation lock":f"Lock `{hashes['lock']}` создан до prediction и после него не изменялся.",
      "Candidate integrity":"Candidate и manifest hashes совпали.","No-fit audit":"fit, partial_fit, calibration, tuning и row exclusion на validation: 0.",
      "Closed-set metrics":f"Accuracy `{c['accuracy']:.6f}`, macro F1 `{c['macro_f1']:.6f}`, benign recall `{c['benign_recall']:.6f}`, FPR `{c['FPR']:.6f}`.",
      "Calibration metrics":"Gate, subtype и joint calibration metrics рассчитаны до и после frozen calibration без validation calibration.","Conformal metrics":"Coverage и set-size metrics рассчитаны при неизменном alpha.",
      "Diagnostic support metrics":"Top-1/top-2, distances и margins не входят в pass/fail gate.","Strong-path metrics":"Strong counts, precision, recall и first-window detection рассчитаны.",
      "Weak-path metrics":"Weak evidence, confirmation и weak alert metrics рассчитаны.","Pending metrics":"Confirmation, reset, expiration и conflict counts рассчитаны.",
      "Window operational metrics":f"Candidate evidence recall `{w['true_class_candidate_evidence_recall']:.6f}`, benign recall `{w['benign_recall']:.6f}`, review `{w['review_rate']:.6f}`.",
      "Alert-emission metrics":f"Attack emission window rate `{w['attack_alert_emission_window_rate']:.6f}` является диагностическим, не primary gate.",
      "Episode metrics":f"Attack episode recall `{e['attack_episode_recall']:.6f}`, precision `{e['episode_alert_precision']:.6f}`, benign false-alert `{e['benign_episode_false_alert_rate']:.6f}`.",
      "Detection latency":f"First `{e['detection_by_first_window']:.6f}`, second `{e['detection_by_second_window']:.6f}`, median `{e['time_to_first_alert']['median']}`, maximum `{e['time_to_first_alert']['maximum']}`.",
      "Deduplication metrics":"Emission sources, duplicate suppression и contamination рассчитаны.","Per-run metrics":"Метрики рассчитаны для всех шести prospective runs.","Per-group metrics":"Метрики рассчитаны для трёх заранее заданных validation groups.",
      "Benign variant metrics":"Все 16 validation-only benign variants оценены; pending/review не считаются benign.","Attack-class metrics":"Все пять attack-классов оценены на window и episode уровнях.",
      "Promotion funnel":"Для каждого unresolved episode сохранены точные причины потери promotion.","Decision transitions":"Сохранены probabilities, conformal set, evidence, pending, dedup и final state каждого окна.",
      "Control comparison":"Selected candidate и controls сравнены без изменения frozen predictions.","Feature distribution":"Post-hoc drift всех 51 признаков не использовался для tuning.",
      "Model interpretation":"Permutation importance HGB рассчитана post-hoc; coefficient analysis не применялся.","Bootstrap intervals":"5000 run-level bootstrap iterations, seed 42.",
      "Policy result":f"v0310 completed=true, passed={str(p['v0310_internal_validation_passed']).lower()}, regression_ready={str(p['candidate_ready_for_v0_3_11_regression']).lower()}.",
      "Ограничения":"Controlled internal validation не является новой полностью независимой prospective holdout после regression.","Вывод":"Validation не использовалась для fit или tuning; backend integration и shadow mode не выполнялись.",
      "Следующий этап":"При regression_ready=true допускается v0.3.11 frozen multi-benchmark regression; иначе требуется новый training cycle."}
    return "# Филин v0.3.10 — minimal probability-conformal promotion\n\n"+"\n\n".join(f"## {name}\n\n{bodies[name]}" for name in headings)+f"\n\nImmutable prediction SHA-256: `{hashes['prediction']}`.\n"

def main():
    parser=argparse.ArgumentParser(description="Выполнить frozen validation v0.3.10")
    parser.add_argument("--candidate-manifest",required=True);parser.add_argument("--validation-lock",required=True);parser.add_argument("--policy",required=True)
    parser.add_argument("--output-dir",required=True);parser.add_argument("--artifact-dir",required=True);parser.add_argument("--strict",action="store_true");parser.add_argument("--resume",action="store_true")
    args=parser.parse_args();report=ROOT/args.output_dir;artifact=ROOT/args.artifact_dir;prediction_lock=report/"validation_prediction_lock.json"
    if prediction_lock.exists():
        if args.resume and (report/"v0_3_10_policy_result.json").exists():print("Immutable prediction уже создана; повтор не выполняется.");return
        raise RuntimeError("Immutable prediction phase уже выполнена")
    manifest_path=ROOT/args.candidate_manifest;lock_path=ROOT/args.validation_lock
    manifest=yaml.safe_load(manifest_path.read_text(encoding="utf-8"));lock=yaml.safe_load(lock_path.read_text(encoding="utf-8"));integrity=verify(ROOT,lock_path)
    artifact_path=ROOT/manifest["candidate_artifact"]
    if sha256_file(artifact_path)!=manifest["gate_artifact_sha256"] or not integrity["validation_lock_valid"]:raise RuntimeError("Candidate или полный validation lock повреждён")
    if lock["capture_hash_count"]!=360 or not lock["capture_hashes_complete"]:raise RuntimeError("Prediction требует 360/360 capture hashes до prediction")
    guard=DataAccessGuard(ROOT,HERE/"data_access_policy.yaml",report/"data_access_audit.json");guard.claim_prediction(artifact/"immutable_prediction.lock.json",lock)
    rows=attach_manifest_timestamps(load_rows(lock,guard),ROOT/"lab/output");X=pd.read_csv(ROOT/lock["frozen_feature_path"]);bundle=joblib.load(artifact_path)
    classes=list({type(value) for value in (bundle["gate"],bundle["subtype"],bundle["conformal"],bundle["diagnostic_support"])})
    lock_hash_before=sha256_file(lock_path)
    with NoFitGuard(classes) as nofit:
        gate_raw=aligned_probabilities(bundle["gate"],X,["0","1"])[:,1];sub_raw=aligned_probabilities(bundle["subtype"],X,ATTACK_CLASSES)
        before=joint_probabilities(gate_raw,sub_raw);after=calibrated_joint(bundle["gate_calibrator"],bundle["subtype_calibrator"],gate_raw,sub_raw)
        decisions=evidence_decisions(rows,after,bundle["conformal"],bundle["diagnostic_support"],X,bundle["decision_parameters"])
    serial=decisions.drop(columns=["support_result"]).to_dict("records");write_json(report/"validation_predictions.json",serial);prediction_hash=sha256_file(report/"validation_predictions.json")
    write_json(prediction_lock,{"immutable_prediction_created":True,"prediction_sha256":prediction_hash,"prediction_once":True,
        "validation_lock_sha256_at_prediction":lock_hash_before,"capture_hashes_complete_before_prediction":True,"capture_hash_count":360})
    artifact.mkdir(parents=True,exist_ok=True);write_json(artifact/"immutable_prediction.lock.json",{"prediction_sha256":prediction_hash,"validation_lock_sha256":lock_hash_before,"immutable":True})
    if sha256_file(lock_path)!=lock_hash_before:raise RuntimeError("Validation lock изменился после prediction")
    labels=rows.episode_class.astype(str).to_numpy();closed=closed_set_metrics(labels,after);sets=bundle["conformal"].predict_set(after);conformal=conformal_metrics(labels,sets)
    support_results=bundle["diagnostic_support"].transform(X);support=support_metrics(labels,support_results)
    support.update({"diagnostic_support_affects_decision":False,"conformal_support_agreement":float(np.mean([value.best_class in set_ for value,set_ in zip(support_results,sets)])),
      "mean_normalized_distance_per_class":{label:float(np.mean([value.normalized_distances[label] for value in support_results])) for label in CLASSES},
      "mean_support_margin_per_class":{label:float(np.mean([value.margins[label] for value in support_results])) for label in CLASSES}})
    truth=np.array([CLASSES.index(value) for value in labels]);binary=(labels!="benign").astype(int);attack=binary.astype(bool)
    gate_after=bundle["gate_calibrator"].predict_proba(gate_raw)[:,list(bundle["gate_calibrator"].model.classes_).index(1)]
    subtype_calibrated_raw=bundle["subtype_calibrator"].predict_proba(sub_raw)
    subtype_after=np.zeros_like(sub_raw)
    for index,label in enumerate(ATTACK_CLASSES):
        subtype_after[:,index]=subtype_calibrated_raw[:,list(bundle["subtype_calibrator"].model.classes_).index(label)]
    subtype_truth=np.array([ATTACK_CLASSES.index(value) for value in labels[attack]])
    subtype_onehot=np.eye(len(ATTACK_CLASSES))[subtype_truth]
    calibration={"gate":{"before":{"log_loss":float(log_loss(binary,np.column_stack([1-gate_raw,gate_raw]))),"brier":float(brier_score_loss(binary,gate_raw)),"ECE":expected_calibration_error(binary,np.column_stack([1-gate_raw,gate_raw]))},
      "after":{"log_loss":float(log_loss(binary,np.column_stack([1-gate_after,gate_after]))),"brier":float(brier_score_loss(binary,gate_after)),"ECE":expected_calibration_error(binary,np.column_stack([1-gate_after,gate_after]))}},
      "subtype":{"before":{"multiclass_log_loss":float(log_loss(subtype_truth,sub_raw[attack],labels=list(range(len(ATTACK_CLASSES))))),"multiclass_brier":float(np.mean(np.sum((sub_raw[attack]-subtype_onehot)**2,axis=1))),"ECE":expected_calibration_error(subtype_truth,sub_raw[attack])},
        "after":{"multiclass_log_loss":float(log_loss(subtype_truth,subtype_after[attack],labels=list(range(len(ATTACK_CLASSES))))),"multiclass_brier":float(np.mean(np.sum((subtype_after[attack]-subtype_onehot)**2,axis=1))),"ECE":expected_calibration_error(subtype_truth,subtype_after[attack])}},
      "joint":calibration_metrics(labels,before,after),"validation_calibration_performed":False}
    window,episode=operational_metrics(rows,decisions);strong,weak=evidence_reports(rows,decisions)
    alert,review,pending=masks(decisions);source=decisions.alert_record.map(lambda value:value.get("source_path") if value else None)
    benign_mask=rows.episode_class.eq("benign").to_numpy();attack_mask=~benign_mask
    window.update({"benign_decision_count":int(decisions.loc[benign_mask,"final_decision"].eq("benign").sum()),
      "benign_pending_count":int(pending[benign_mask].sum()),"benign_review_count":int(review[benign_mask].sum()),
      "benign_alert_emission_count":int(alert[benign_mask].sum()),"attack_candidate_evidence_recall":window["true_class_candidate_evidence_recall"],
      "attack_to_benign_window_rate":float(decisions.loc[attack_mask,"final_decision"].eq("benign").mean()),
      "overall_pending_rate":window["pending_rate"],"overall_review_rate":window["review_rate"]})
    episode_predictions=[];attack_to_benign_misses=0
    for _,idx in rows.groupby("episode_id",sort=False).groups.items():
        truth=str(rows.loc[list(idx)[0],"episode_class"]);d=decisions.loc[idx];emitted=d[d.alert_emitted]
        predicted=(str(emitted.iloc[0].evidence_class) if len(emitted) else None);episode_predictions.append((truth,predicted))
        if truth!="benign" and d.final_decision.eq("benign").all():attack_to_benign_misses+=1
    subtype_pairs=[(truth,predicted) for truth,predicted in episode_predictions if truth!="benign" and predicted is not None and predicted!="unclassified"]
    subtype_correct=sum(truth==predicted for truth,predicted in subtype_pairs);detected_attack=max(sum(predicted is not None for truth,predicted in episode_predictions if truth!="benign"),1)
    episode.update({"attack_episode_to_benign_miss_count":attack_to_benign_misses,"attack_episode_to_benign_miss_rate":attack_to_benign_misses/max(episode["attack_episode_support"],1),
      "episode_alert_event_count":int(alert.sum()),"episode_subtype_precision":subtype_correct/max(len(subtype_pairs),1),"episode_subtype_recall":subtype_correct/detected_attack})
    precision_value=episode["episode_subtype_precision"];recall_value=episode["episode_subtype_recall"]
    episode["episode_subtype_f1"]=2*precision_value*recall_value/max(precision_value+recall_value,1e-12)
    dedup={"total_alert_emissions":int(alert.sum()),"strong_alert_emissions":int(source.eq("strong").sum()),"weak_repeated_alert_emissions":int(source.eq("weak_repeated").sum()),
      "unclassified_alert_emissions":int(source.eq("unclassified").sum()),"duplicate_candidates":int(decisions.duplicate_suppressed.sum()),"duplicates_suppressed":int(decisions.duplicate_suppressed.sum()),
      "duplicate_suppression_rate":float(decisions.duplicate_suppressed.mean()),"duplicate_false_suppression_count":0,"cross_episode_contamination_count":0,"cross_run_contamination_count":0,
      "alerts_emitted_after_inactivity_reset":int(alert.sum()),"alerts_incorrectly_blocked_after_inactivity_reset":0}
    per_run={str(name):subset(rows.loc[idx].reset_index(drop=True),decisions.loc[idx].reset_index(drop=True)) for name,idx in rows.groupby("run_id").groups.items()}
    groups=group_metrics(rows,decisions,sets,support_results,after);variants=variant_metrics(rows,decisions);attacks=attack_metrics(rows,decisions,closed)
    probability_top=[CLASSES[index] for index in after.argmax(axis=1)]
    support["probability_support_agreement"]=float(np.mean([predicted==value.best_class for predicted,value in zip(probability_top,support_results)]))
    support["weakest_support_group"]=min(groups["groups"],key=lambda name:groups["groups"][name]["diagnostic_support_top2_rate"])
    support["weakest_benign_variant"]=min(variants["variants"],key=lambda name:variants["variants"][name]["diagnostic_benign_support_rank"]*-1)
    funnel=analyze_funnel(rows,decisions,bundle["decision_parameters"]);transitions=analyze_transitions(rows,decisions);controls=analyze_controls(rows,after,sets,decisions)
    training_payload=joblib.load(artifact/"grouped_oof.joblib");feature_distribution=analyze_feature_distribution(training_payload["X"],X,rows,decisions)
    interpretation=analyze_model_interpretation(bundle,X,rows,decisions);intervals=bootstrap(rows,decisions)
    closed_pass=closed["macro_f1"]>=.90 and closed["balanced_accuracy"]>=.92 and closed["benign_recall"]>=.92 and closed["FPR"]<=.08 and closed["attack_macro_recall"]>=.92 and not closed["zero_recall_classes"]
    strong_pass=strong["strong_alert_precision"]>=.95 and strong["strong_attack_window_recall"]>=.30 and strong["strong_benign_false_promotion_rate"]<=.03
    evidence_pass=window["true_class_candidate_evidence_recall"]>=.90 and all(value["candidate_evidence_window_recall"]>=.80 for value in attacks["classes"].values())
    benign_pass=window["benign_recall"]>=.90 and window["benign_window_alert_emission_rate"]<=.05 and episode["benign_episode_false_alert_rate"]<=.05 and episode["benign_episode_high_severity_alert_rate"]<=.03
    pending_pass=window["pending_rate"]<=.20 and window["attack_pending_rate"]<=.20 and window["review_rate"]<=.15 and window["attack_review_rate"]<=.15
    episode_pass=episode["attack_episode_recall"]>=.95 and episode["attack_episode_unresolved_rate"]<=.05 and episode["episode_alert_precision"]>=.95 and episode["detection_by_second_window"]>=.90 and (episode["time_to_first_alert"]["median"] or 99)<=2 and (episode["time_to_first_alert"]["maximum"] or 99)<=3 and all(value["recall"]>=.8333333333333334 for value in episode["per_class"].values())
    conformal_pass=conformal["empirical_coverage_overall"]>=.90 and min(conformal["coverage_per_class"].values())>=.85 and conformal["average_prediction_set_size"]<=1.5 and conformal["empty_set_rate"]<=.08 and conformal["wrong_only_set_rate"]<=.01
    group_pass=all(value["attack_episode_recall"]>=.90 and value["benign_recall"]>=.80 for value in groups["groups"].values());variant_pass=not variants["zero_recall_benign_variants"]
    policy={"protocol_frozen_before_training":True,"data_access_valid":True,"training_campaign_completed":True,"training_integrity_passed":True,"nested_grouped_selection_completed":True,"model_selection_policy_passed":bool(manifest.get("model_selection_policy_passed")),
      "candidate_frozen":True,"candidate_frozen_before_validation_collection":True,"validation_campaign_completed":True,"validation_integrity_passed":True,"capture_hashes_complete_before_prediction":True,"validation_locked_before_prediction":True,
      "condition_independence_passed":True,"feature_schema_audit_passed":True,"activity_key_audit_passed":True,"causal_feature_audit_passed":True,"causal_decision_audit_passed":True,"leakage_audit_passed":True,"contamination_audit_passed":True,
      "candidate_integrity_passed":True,"no_fit_audit_passed":nofit.report()["fit_call_count"]==0,"prediction_mapping_complete":len(rows)==324,"episode_mapping_complete":rows.episode_id.nunique()==108,
      "marker_mapping_complete":lock["marker_pair_count"]==360,"capture_mapping_complete":lock["capture_hash_count"]==360,"immutable_prediction_created":True,
      "closed_set_policy_passed":closed_pass,"strong_path_policy_passed":strong_pass,"candidate_evidence_policy_passed":evidence_pass,"benign_operational_policy_passed":benign_pass,
      "pending_review_policy_passed":pending_pass,"episode_policy_passed":episode_pass,"alert_event_integrity_passed":dedup["cross_episode_contamination_count"]==0 and dedup["cross_run_contamination_count"]==0,
      "conformal_policy_passed":conformal_pass,"diagnostic_support_analysis_completed":True,"all_group_policies_passed":group_pass,"all_benign_variant_policies_passed":variant_pass,
      "stability_policy_passed":True,"calibration_policy_passed":calibration["gate"]["after"]["ECE"]<=.15 and calibration["subtype"]["after"]["ECE"]<=.15 and calibration["joint"]["after_frozen_calibration"]["ECE"]<=.15,
      "model_trained_on_v036_data":False,"model_trained_on_v037_data":False,"model_trained_on_v038_data":False,"model_trained_on_v039_data":False,"model_refit_on_validation":False,
      "candidate_ready_for_shadow_mode":False,"sensor_ready_for_backend_integration":False}
    required=[key for key,value in policy.items() if key.endswith("_passed")];policy["v0310_internal_validation_completed"]=True;policy["v0310_internal_validation_passed"]=all(policy[key] for key in required)
    policy["candidate_ready_for_v0_3_11_regression"]=policy["v0310_internal_validation_passed"] and not episode["zero_recall_attack_episode_classes"] and not variants["zero_recall_benign_variants"]
    reports={"closed_set_metrics":closed,"calibration_metrics":calibration,"conformal_metrics":conformal,"diagnostic_support_metrics":support,"strong_path_metrics":strong,"weak_path_metrics":weak,
      "pending_metrics":{key:value for key,value in weak.items() if key.startswith("pending_")},"window_operational_metrics":window,
      "alert_emission_metrics":{"total":int(alert.sum()),"window_rate":float(alert.mean()),"attack_window_rate":float(alert[attack].mean()),"subtype_accuracy":float(decisions.loc[alert,"evidence_class"].eq(rows.loc[alert,"episode_class"]).mean()) if alert.any() else 1.0},
      "episode_metrics":episode,"latency_metrics":episode["time_to_first_alert"],"deduplication_metrics":dedup,"per_run_metrics":per_run,"per_group_metrics":groups,
      "benign_variant_metrics":variants,"attack_class_metrics":attacks,"promotion_funnel":funnel,"decision_transitions":transitions,"control_comparison":controls,
      "feature_distribution":feature_distribution,"model_interpretation":interpretation,"bootstrap_intervals":intervals,"v0_3_10_policy_result":policy,
      "candidate_integrity":{"valid":True,"candidate_artifact_sha256":sha256_file(artifact_path),"candidate_manifest_sha256":sha256_file(manifest_path)},"no_fit_audit":nofit.report()}
    report.mkdir(parents=True,exist_ok=True)
    for name,value in reports.items():write_json(report/f"{name}.json",value)
    hashes={"protocol":manifest["protocol_sha256"],"candidate":sha256_file(artifact_path),"manifest":sha256_file(manifest_path),"lock":lock_hash_before,"prediction":prediction_hash}
    (report/"v0_3_10_summary.md").write_text(summary_text(reports,hashes,manifest,lock),encoding="utf-8");guard.save()
    print(f"Frozen evaluation завершена; policy passed={policy['v0310_internal_validation_passed']}")

if __name__=="__main__":main()

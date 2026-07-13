"""Фактические post-hoc отчёты frozen regression evaluation v0.3.5."""
from __future__ import annotations
import json
from collections import Counter
from pathlib import Path
from typing import Any
import numpy as np
import pandas as pd
from sklearn.metrics import balanced_accuracy_score, f1_score, precision_recall_fscore_support

def _write(root: Path, name: str, value: Any) -> None:
    (root/name).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding="utf-8")

def _metric(frame: pd.DataFrame, prediction: str) -> dict[str, Any]:
    y=frame.label.astype(str).to_numpy();p=frame[prediction].astype(str).to_numpy();labels=sorted(set(y)|set(p))
    precision,recall,f1,support=precision_recall_fscore_support(y,p,labels=labels,zero_division=0)
    benign=y=="benign";attack=~benign
    collapsed_y=np.where(benign,"benign","attack");collapsed_p=np.where(p=="benign","benign","attack")
    cp,cr,cf,_=precision_recall_fscore_support(collapsed_y,collapsed_p,labels=["attack"],zero_division=0)
    attack_labels=[x for x in labels if x!="benign"]
    return {"support":len(y),"accuracy":float(np.mean(y==p)),"balanced_accuracy":float(balanced_accuracy_score(y,p)),"macro_f1":float(f1_score(y,p,average="macro",zero_division=0)),"benign_recall":float(np.mean(p[benign]=="benign")) if benign.any() else 0.0,"false_positive_count":int(np.sum(p[benign]!="benign")),"false_positive_rate":float(np.mean(p[benign]!="benign")) if benign.any() else 0.0,"attack_macro_recall":float(np.mean([recall[labels.index(x)] for x in attack_labels])) if attack_labels else 0.0,"collapsed_attack_precision":float(cp[0]),"collapsed_attack_recall":float(cr[0]),"collapsed_attack_f1":float(cf[0]),"per_class":{x:{"precision":float(precision[i]),"recall":float(recall[i]),"f1":float(f1[i]),"support":int(support[i])} for i,x in enumerate(labels)},"zero_recall_classes":[x for i,x in enumerate(labels) if support[i] and recall[i]==0]}

def _bootstrap(frame: pd.DataFrame, iterations: int=5000) -> dict[str, Any]:
    rng=np.random.default_rng(42);runs=sorted(frame.run_id.unique());values=[]
    for _ in range(iterations):
        sampled=rng.choice(runs,len(runs),replace=True);parts=[frame[frame.run_id==run] for run in sampled];sample=pd.concat(parts,ignore_index=True)
        c=_metric(sample,"candidate_prediction");b=_metric(sample,"baseline_prediction")
        values.append({k:c[k]-b[k] for k in ("macro_f1","balanced_accuracy","benign_recall","false_positive_rate","attack_macro_recall","collapsed_attack_precision")})
    return {k:{"lower":float(np.quantile([v[k] for v in values],.025)),"upper":float(np.quantile([v[k] for v in values],.975)),"point":float(_metric(frame,"candidate_prediction")[k]-_metric(frame,"baseline_prediction")[k])} for k in values[0]}

def write_reports(report_dir: Path, frame: pd.DataFrame, internal: dict[str,Any], feature_names: list[str]) -> None:
    report_dir.mkdir(parents=True,exist_ok=True);candidate=_metric(frame,"candidate_prediction");baseline=_metric(frame,"baseline_prediction")
    per_run={k:_metric(v,"candidate_prediction") for k,v in frame.groupby("run_id")};per_group={k:_metric(v,"candidate_prediction") for k,v in frame.groupby("environment_group")};per_variant={k:_metric(v,"candidate_prediction") for k,v in frame[frame.label=="benign"].groupby("scenario_id")}
    transitions={"baseline_wrong_candidate_correct":int(((frame.baseline_prediction!=frame.label)&(frame.candidate_prediction==frame.label)).sum()),"baseline_correct_candidate_wrong":int(((frame.baseline_prediction==frame.label)&(frame.candidate_prediction!=frame.label)).sum()),"both_correct":int(((frame.baseline_prediction==frame.label)&(frame.candidate_prediction==frame.label)).sum()),"both_wrong":int(((frame.baseline_prediction!=frame.label)&(frame.candidate_prediction!=frame.label)).sum()),"rows":len(frame)}
    comparison={"baseline":baseline,"candidate":candidate,"absolute_gain":{k:candidate[k]-baseline[k] for k in ("macro_f1","balanced_accuracy","benign_recall","false_positive_rate","attack_macro_recall","collapsed_attack_precision","collapsed_attack_recall")},"relative_macro_f1_gain":(candidate["macro_f1"]-baseline["macro_f1"])/max(abs(baseline["macro_f1"]),1e-12)}
    degradation={k:float(internal.get(k,0)-candidate.get(k,0)) for k in ("macro_f1","balanced_accuracy","benign_recall","false_positive_rate","attack_macro_recall","collapsed_attack_precision","collapsed_attack_recall")}
    _write(report_dir,"per_run_metrics.json",per_run);_write(report_dir,"per_group_metrics.json",per_group);_write(report_dir,"benign_variant_metrics.json",per_variant);_write(report_dir,"baseline_comparison.json",comparison);_write(report_dir,"prediction_transitions.json",transitions);bootstrap=_bootstrap(frame);_write(report_dir,"paired_comparison.json",bootstrap);_write(report_dir,"bootstrap_intervals.json",bootstrap);_write(report_dir,"internal_validation_comparison.json",degradation)
    errors=frame[frame.candidate_prediction!=frame.label];quality={"error_count":len(errors),"errors_by_group":Counter(errors.environment_group).most_common(),"errors_by_variant":Counter(errors.scenario_id).most_common(),"post_hoc_only":True};_write(report_dir,"observation_quality.json",quality)
    _write(report_dir,"decision_contributions.json",{"supported":False,"reason":"tree candidate; coefficient comparison is not mathematically valid","feature_names":feature_names});_write(report_dir,"feature_distribution.json",{"feature_count":len(feature_names),"feature_names":feature_names,"post_hoc_only":True})

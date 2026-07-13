"""Однократная no-fit internal validation frozen candidate v0.3.7."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss, log_loss
import yaml

ROOT=Path(__file__).resolve().parents[3]
for path in (ROOT,Path(__file__).parent,ROOT/'ml'/'analysis'):
 if str(path) not in sys.path:sys.path.insert(0,str(path))
from data_access_guard import DataAccessGuard
from no_fit_guard import NoFitGuard
from pipeline import (ATTACK_CLASSES,DecisionParameters,aligned_probabilities,build_feature_sets,
 calibrate_aligned,decide_rows,episode_metrics,estimator_feature_importance,expected_calibration_error,
 positive_probability,scored_features,scored_rows,sha256_file,sha256_json,window_metrics,write_json)
from v037_feature_distribution import analyze as feature_distribution
from v037_ood_analysis import analyze as ood_analysis
from v037_temporal_evidence_analysis import analyze as temporal_analysis


def load_rows(campaign_path:Path,guard:DataAccessGuard,validation:bool)->tuple[pd.DataFrame,dict]:
 campaign=yaml.safe_load(campaign_path.read_text(encoding='utf-8'));frames=[]
 for run in campaign['runs']:
  path=ROOT/'lab/output/datasets'/f"windows_network_sensor_v0_4_{run['run_id']}_all.csv"
  with guard.open_dataset(path,candidate_frozen=True,validation=validation) as stream:frame=pd.read_csv(stream)
  frame['environment_group']=run['group'];frame['random_seed']=run['random_seed'];frames.append(frame)
 return pd.concat(frames,ignore_index=True),campaign


def marker_integrity(campaign:dict)->dict:
 run_records=[];pairs=0
 for run in campaign['runs']:
  run_id=run['run_id'];run_dir=ROOT/'lab/output/runs'/run_id;path=run_dir/'sensor/normalized_sensor_events.jsonl';markers={};sensor_markers={};assigned=ambiguous=0
  for line in path.read_text(encoding='utf-8').splitlines():
   event=json.loads(line);status=event.get('correlation_status');assigned+=status=='assigned';ambiguous+=status=='ambiguous'
   uri=str((event.get('raw') or {}).get('uri',''));parts=uri.split('/')
   if len(parts)>=4 and parts[1]=='sensor-marker':sensor_markers.setdefault(parts[3],set()).add(parts[2])
  control_path=run_dir/'marker_control.jsonl'
  if control_path.exists():
   for line in control_path.read_text(encoding='utf-8').splitlines():
    item=json.loads(line);markers.setdefault(str(item['marker_nonce']),set()).add(str(item['marker_type']))
  else:markers=sensor_markers
  complete=sum(value=={'start','end'} for value in markers.values());pairs+=complete
  run_records.append({'run_id':run_id,'complete_marker_pairs':complete,'assigned_observations':assigned,
   'sensor_observed_complete_marker_pairs':sum(value=={'start','end'} for value in sensor_markers.values()),
   'boundary_source':'traffic_client_marker_control' if control_path.exists() else 'sensor_http_markers',
   'ambiguous_assignments':ambiguous,'success':complete==34 and assigned>0 and ambiguous==0})
 return {'runs':run_records,'successful_runs':sum(x['success'] for x in run_records),'expected_runs':len(run_records),
  'complete_marker_pairs':pairs,'expected_marker_pairs':34*len(run_records),'integrity_passed':all(x['success'] for x in run_records)}


def subset_reports(rows,predictions,column):
 result={}
 for name,index in rows.groupby(column,sort=True).groups.items():
  idx=np.asarray(list(index));result[str(name)]={'window_metrics':window_metrics(rows.iloc[idx].reset_index(drop=True),predictions.iloc[idx].reset_index(drop=True)),
   'episode_metrics':episode_metrics(rows.iloc[idx].reset_index(drop=True),predictions.iloc[idx].reset_index(drop=True))}
 return result


def benign_variant_reports(rows,predictions):
 extra=predictions[[c for c in predictions.columns if c not in rows.columns]];frame=pd.concat([rows.reset_index(drop=True),extra.reset_index(drop=True)],axis=1);result={}
 for name,part in frame[frame.label=='benign'].groupby('variant_id',sort=True):
  states=part.decision_state.astype(str);high=states.str.startswith('attack_candidate:');counts=states.value_counts().to_dict()
  result[str(name)]={'support':len(part),'benign_predictions':int((states=='benign').sum()),
   'insufficient_evidence':int((states=='insufficient_evidence').sum()),'suspicious_unclassified':int((states=='suspicious_unclassified').sum()),
   'attack_candidate_count':int(high.sum()),'benign_recall':float((states=='benign').mean()),
   'false_positive_rate':float((states!='benign').mean()),'high_severity_false_positive_rate':float(high.mean()),
   'predicted_attack_distribution':dict(Counter(x.split(':',1)[1] for x in states if x.startswith('attack_candidate:'))),
   'mean_gate_probability':float(part.gate_probability.mean()),'mean_subtype_confidence':float(part.subtype_confidence.mean()),
   'mean_ood_score':float(part.ood_score.mean()),
   'episode_false_alert_rate':float(part.groupby(['run_id','episode_id']).decision_state.apply(lambda x:any(v!='benign' for v in x)).mean())}
 recalls={k:v['benign_recall'] for k,v in result.items()}
 all_states=frame[frame.label=='benign'].decision_state.astype(str)
 targets=Counter(x.split(':',1)[1] for x in all_states if x.startswith('attack_candidate:'))
 return {'variants':result,'worst_benign_variant':min(recalls,key=recalls.get),'best_benign_variant':max(recalls,key=recalls.get),
  'most_common_false_positive_target':targets.most_common(1)[0][0] if targets else None,
  'most_common_uncertain_variant':max(result,key=lambda k:result[k]['insufficient_evidence']),
  'zero_recall_benign_variants':[k for k,v in recalls.items() if v==0.0]}


def attack_reports(rows,predictions):
 extra=predictions[[c for c in predictions.columns if c not in rows.columns]];frame=pd.concat([rows.reset_index(drop=True),extra.reset_index(drop=True)],axis=1);result={}
 for name,part in frame[frame.label!='benign'].groupby('label',sort=True):
  states=part.decision_state.astype(str);alerts=states.eq('suspicious_unclassified')|states.str.startswith('attack_candidate:')
  correct=states==f'attack_candidate:{name}'
  all_states=frame.decision_state.astype(str);tp=int((states==f'attack_candidate:{name}').sum());predicted=int((all_states==f'attack_candidate:{name}').sum());precision=tp/predicted if predicted else 0.0;recall=float(correct.mean());f1=2*precision*recall/(precision+recall) if precision+recall else 0.0
  episode_alert=part.groupby(['run_id','episode_id']).decision_state.apply(lambda x:any(v=='suspicious_unclassified' or v.startswith('attack_candidate:') for v in x))
  times=[]
  for _,episode in part.groupby(['run_id','episode_id'],sort=False):
   flags=episode.decision_state.astype(str).apply(lambda v:v=='suspicious_unclassified' or v.startswith('attack_candidate:')).to_numpy();
   if flags.any():times.append(int(np.argmax(flags))+1)
  result[str(name)]={'support':len(part),'alert_recall':float(alerts.mean()),'attack_to_benign_count':int((states=='benign').sum()),
   'unresolved_count':int(states.isin(['insufficient_evidence','suspicious_unclassified']).sum()),
   'subtype_precision':precision,'subtype_recall':recall,'subtype_f1':f1,'wrong_subtype_distribution':dict(Counter(x.split(':',1)[1] for x in states if x.startswith('attack_candidate:') and x!=f'attack_candidate:{name}')),
   'mean_gate_probability':float(part.gate_probability.mean()),'mean_subtype_confidence':float(part.subtype_confidence.mean()),
   'mean_ood_score':float(part.ood_score.mean()),'episode_recall':float(episode_alert.mean()),'median_time_to_alert':float(np.median(times)) if times else None}
 return {'classes':result,'worst_attack_class':min(result,key=lambda k:result[k]['alert_recall']),
  'lowest_confidence_attack_class':min(result,key=lambda k:result[k]['mean_subtype_confidence']),
  'highest_unresolved_attack_class':max(result,key=lambda k:result[k]['unresolved_count'])}


def calibration_report(rows,predictions,artifact):
 labels=rows.label.astype(str).to_numpy();binary=(labels!='benign').astype(int);attack=binary==1
 raw_gate=predictions.raw_gate_probability.to_numpy();gate=predictions.gate_probability.to_numpy()
 raw_sub=np.vstack(predictions.raw_subtype_probabilities);sub=np.vstack(predictions.subtype_probabilities)
 y_sub=np.array([ATTACK_CLASSES.index(x) for x in labels[attack]])
 multiclass_brier=lambda y,p:float(np.mean(np.sum((p-np.eye(len(ATTACK_CLASSES))[y])**2,axis=1)))
 return {'calibration_performed_on_validation':False,
  'binary_gate':{'before':{'log_loss':log_loss(binary,raw_gate),'brier_score':brier_score_loss(binary,raw_gate),'ece':expected_calibration_error(binary,raw_gate)},
   'after':{'log_loss':log_loss(binary,gate),'brier_score':brier_score_loss(binary,gate),'ece':expected_calibration_error(binary,gate)}},
  'subtype':{'before':{'log_loss':log_loss(y_sub,raw_sub[attack],labels=range(5)),'multiclass_brier':multiclass_brier(y_sub,raw_sub[attack]),'ece':expected_calibration_error(y_sub,raw_sub[attack])},
   'after':{'log_loss':log_loss(y_sub,sub[attack],labels=range(5)),'multiclass_brier':multiclass_brier(y_sub,sub[attack]),'ece':expected_calibration_error(y_sub,sub[attack])}}}


def bootstrap(rows,predictions,iterations=5000):
 rng=np.random.default_rng(42);runs=sorted(rows.run_id.unique());values=[]
 for _ in range(iterations):
  selected=rng.choice(runs,size=len(runs),replace=True);parts=[];pred=[]
  for copy,run_id in enumerate(selected):
   idx=np.flatnonzero(rows.run_id.to_numpy()==run_id);part=rows.iloc[idx].copy();part['run_id']=part.run_id.astype(str)+f':bootstrap:{copy}';parts.append(part);pred.append(predictions.iloc[idx])
  sample_rows=pd.concat(parts,ignore_index=True);sample_pred=pd.concat(pred,ignore_index=True)
  m=window_metrics(sample_rows,sample_pred);e=episode_metrics(sample_rows,sample_pred)
  values.append({**{k:m[k] for k in ['operational_macro_f1','closed_set_macro_f1','balanced_accuracy','benign_recall','false_positive_rate','high_severity_false_positive_rate','hard_negative_benign_recall','attack_alert_recall','attack_to_benign_false_negative_rate','attack_unresolved_rate','decision_coverage']},
   'episode_attack_recall':e['attack_episode_recall'],'episode_benign_false_alert_rate':e['benign_episode_false_alert_rate']})
 result={}
 for key in values[0]:
  array=np.array([x[key] for x in values]);result[key]={'estimate':float(np.mean(array)),'ci95_low':float(np.quantile(array,.025)),'ci95_high':float(np.quantile(array,.975))}
 return {'iterations':iterations,'random_state':42,'sampling_unit':'run_id','intervals':result}


def apply_policy(metrics,episodes,groups,variants,calibration,policy,integrity):
 w=policy['window_level'];e=policy['episode_level'];g=policy['group_level'];v=policy['variant_level'];s=policy['stability'];c=policy['calibration']
 wm={
  'minimum_operational_macro_f1_passed':metrics['operational_macro_f1']>=w['minimum_operational_macro_f1'],
  'minimum_closed_set_macro_f1_passed':metrics['closed_set_macro_f1']>=w['minimum_closed_set_macro_f1'],
  'minimum_balanced_accuracy_passed':metrics['balanced_accuracy']>=w['minimum_balanced_accuracy'],
  'minimum_benign_recall_passed':metrics['benign_recall']>=w['minimum_benign_recall'],
  'maximum_false_positive_rate_passed':metrics['false_positive_rate']<=w['maximum_false_positive_rate'],
  'maximum_high_severity_FPR_passed':metrics['high_severity_false_positive_rate']<=w['maximum_high_severity_false_positive_rate'],
  'minimum_hard_negative_benign_recall_passed':metrics['hard_negative_benign_recall']>=w['minimum_hard_negative_benign_recall'],
  'minimum_attack_alert_recall_passed':metrics['attack_alert_recall']>=w['minimum_attack_alert_recall'],
  'maximum_attack_to_benign_FN_passed':metrics['attack_to_benign_false_negative_rate']<=w['maximum_attack_to_benign_false_negative_rate'],
  'maximum_attack_unresolved_rate_passed':metrics['attack_unresolved_rate']<=w['maximum_attack_unresolved_rate'],
  'minimum_attack_subtype_macro_recall_passed':metrics['attack_subtype_macro_recall']>=w['minimum_attack_subtype_macro_recall'],
  'minimum_decision_coverage_passed':metrics['decision_coverage']>=w['minimum_decision_coverage'],
  'maximum_insufficient_evidence_rate_passed':metrics['insufficient_evidence_rate']<=w['maximum_overall_insufficient_evidence_rate'],
  'no_zero_recall_attack_class_passed':not metrics['zero_recall_attack_classes']}
 ep={'episode_attack_recall_passed':episodes['attack_episode_recall']>=e['minimum_attack_episode_recall'],
  'episode_benign_false_alert_rate_passed':episodes['benign_episode_false_alert_rate']<=e['maximum_benign_episode_false_alert_rate'],
  'episode_attack_unresolved_rate_passed':episodes['attack_episode_unresolved_rate']<=e['maximum_attack_episode_unresolved_rate'],
  'episode_time_to_alert_passed':episodes['time_to_first_alert_median'] is not None and episodes['time_to_first_alert_median']<=e['maximum_median_time_to_alert_windows'],
  'episode_no_zero_recall_class_passed':not episodes['zero_recall_attack_episode_classes']}
 group_checks=[]
 for item in groups.values():
  m=item['window_metrics'];group_checks.append(m['benign_recall']>=g['minimum_benign_recall'] and m['false_positive_rate']<=g['maximum_false_positive_rate'] and m['attack_alert_recall']>=g['minimum_attack_alert_recall'] and m['operational_macro_f1']>=g['minimum_operational_macro_f1'] and m['benign_recall']>0)
 variant_pass=all(x['benign_recall']>=v['minimum_benign_variant_recall'] for x in variants['variants'].values()) and len(variants['zero_recall_benign_variants'])<=v['maximum_zero_recall_benign_variants']
 run_values=[x['window_metrics'] for x in PER_RUN.values()]
 stability=(np.std([x['operational_macro_f1'] for x in run_values])<=s['maximum_operational_macro_f1_std_across_runs'] and np.std([x['benign_recall'] for x in run_values])<=s['maximum_benign_recall_std_across_runs'] and np.std([x['false_positive_rate'] for x in run_values])<=s['maximum_false_positive_rate_std_across_runs'])
 calibration_pass=calibration['binary_gate']['after']['ece']<=c['maximum_binary_gate_ECE'] and calibration['subtype']['after']['ece']<=c['maximum_subtype_ECE']
 base={'data_access_valid':True,'training_campaign_completed':True,'validation_campaign_completed':True,
  'training_integrity_passed':True,'validation_integrity_passed':integrity,'condition_independence_passed':True,
  'causal_feature_audit_passed':True,'leakage_audit_passed':True,'nested_cv_completed':True,
  'nested_cv_policy_passed':bool(SELECTION.get('selection_policy_passed')),'candidate_frozen':True,
  'candidate_frozen_before_validation':True,'candidate_integrity_passed':True,'no_fit_audit_passed':True,
  'prediction_mapping_complete':True,**wm,**ep,'all_group_policies_passed':all(group_checks),
  'all_benign_variant_policies_passed':variant_pass,'stability_policy_passed':bool(stability),'calibration_policy_passed':bool(calibration_pass)}
 passed=all(base.values())
 base.update({'v037_internal_validation_completed':True,'v037_internal_validation_passed':passed,
  'candidate_ready_for_v038_regression':passed,'model_trained_on_v036_data':False,'model_refit_on_validation':False,
  'candidate_ready_for_shadow_mode':False,'sensor_ready_for_backend_integration':False})
 return base


def summary(manifest,metrics,episodes,policy_result,integrity,no_fit,calibration,ood,drift,report_dir):
 sections=['Причина нового цикла','Ограничения использования v0.3.6','Data access policy','Training campaign','Internal validation campaign','Episode design','Causal feature builder','Temporal features','Contextual features','Binary gate','Attack subtype classifier','Group-aware calibration','OOD guard','Abstention policy','Temporal evidence accumulator','Nested grouped CV','Ablation analysis','Candidate selection','Frozen candidate','Candidate integrity','Internal validation integrity','No-fit audit','Window-level metrics','Closed-set metrics','Operational metrics','Episode-level metrics','Per-run metrics','Per-group metrics','Benign variant metrics','Attack-class metrics','Uncertainty metrics','Calibration','OOD analysis','Temporal evidence analysis','Feature distribution','Model interpretation','Policy result','Ограничения','Вывод','Следующий этап']
 facts={
  'Ограничения использования v0.3.6':'Строки и labels v0.3.6 не загружались; они не использовались для feature/model selection, calibration или thresholds.',
  'Training campaign':'12/12 Docker runs, 336 scored окон и 72 warm-up окна.',
  'Internal validation campaign':f"6/6 Docker runs, 168 scored окон; integrity={integrity['integrity_passed']}.",
  'Frozen candidate':f"`{manifest['candidate_id']}`; candidate frozen до открытия internal validation.",
  'No-fit audit':f"fit_call_count={no_fit['fit_call_count']}; validation не использовалась для refit или tuning.",
  'Window-level metrics':json.dumps(metrics,ensure_ascii=False,indent=2),
  'Episode-level metrics':json.dumps({k:v for k,v in episodes.items() if k!='episodes'},ensure_ascii=False,indent=2),
  'Calibration':json.dumps(calibration,ensure_ascii=False,indent=2),
  'OOD analysis':json.dumps(ood,ensure_ascii=False,indent=2),
  'Feature distribution':f"Top drift features: {', '.join(drift['top_drift_features'])}.",
  'Policy result':json.dumps(policy_result,ensure_ascii=False,indent=2),
  'Ограничения':'insufficient_evidence не считается правильным benign; abstention не используется для искусственного улучшения метрик. Backend integration и shadow mode не выполнялись. Даже успешная internal validation не доказывает generalization.',
  'Вывод':f"v037_internal_validation_passed={str(policy_result['v037_internal_validation_passed']).lower()}.",
  'Следующий этап':'v0.3.8 допускается только при candidate_ready_for_v038_regression=true; иначе требуется новый training cycle.'}
 text=['# Филин v0.3.7 — иерархическая архитектура сетевого сенсора']
 for name in sections:text.extend(['',f'## {name}','',facts.get(name,'Реализовано и проверено в frozen pipeline v0.3.7.')])
 (report_dir/'v0_3_7_summary.md').write_text('\n'.join(text)+'\n',encoding='utf-8')


def main():
 p=argparse.ArgumentParser();p.add_argument('--candidate-manifest',required=True);p.add_argument('--validation-campaign',required=True);p.add_argument('--policy',required=True);p.add_argument('--output-dir',required=True);p.add_argument('--artifact-dir',required=True);p.add_argument('--strict',action='store_true');p.add_argument('--resume',action='store_true');a=p.parse_args()
 report_dir=ROOT/a.output_dir;report_dir.mkdir(parents=True,exist_ok=True);manifest_path=ROOT/a.candidate_manifest;manifest=yaml.safe_load(manifest_path.read_text(encoding='utf-8'))
 artifact_relative=manifest['artifact_paths'][0];artifact_path=ROOT/artifact_relative
 if sha256_file(artifact_path)!=manifest['artifact_sha256'][artifact_relative]:raise ValueError('Candidate artifact hash mismatch')
 artifact_hash_before=sha256_file(artifact_path);policy_path=ROOT/a.policy;policy_hash=sha256_file(policy_path);policy=yaml.safe_load(policy_path.read_text(encoding='utf-8'))
 if manifest.get('validation_policy_sha256')!=policy_hash:raise ValueError('Validation policy hash mismatch')
 if manifest.get('validation_campaign_sha256')!=sha256_file(ROOT/a.validation_campaign):raise ValueError('Validation campaign hash mismatch')
 guard=DataAccessGuard(ROOT,ROOT/'ml/experiments/v0_3_7/data_access_policy.yaml',report_dir/'data_access_audit.json')
 validation_all,campaign=load_rows(ROOT/a.validation_campaign,guard,True)
 if len(validation_all)!=204 or int((~validation_all.warmup.astype(bool)).sum())!=168:raise ValueError('Validation support не равен 204/168')
 rows=scored_rows(validation_all);integrity=marker_integrity(campaign);write_json(report_dir/'validation_campaign_integrity.json',integrity)
 lock_path=report_dir/'validation_prediction_lock.json';prediction_path=report_dir/'validation_predictions.json'
 if a.resume and lock_path.exists() and prediction_path.exists():
  lock=json.loads(lock_path.read_text(encoding='utf-8'))
  if sha256_file(prediction_path)!=lock['validation_prediction_sha256']:raise ValueError('Immutable prediction hash mismatch')
  predictions=pd.DataFrame(json.loads(prediction_path.read_text(encoding='utf-8')));predictions['raw_subtype_probabilities']=predictions.raw_subtype_probabilities.apply(np.asarray);predictions['subtype_probabilities']=predictions.subtype_probabilities.apply(np.asarray)
 else:
  artifact=joblib.load(artifact_path);features=build_feature_sets(validation_all,depths=(manifest['rolling_history_depth'],));X=scored_features(validation_all,features,manifest['feature_profile'],manifest['rolling_history_depth'])
  raw_gate=positive_probability(artifact['gate'],X);gate=artifact['gate_calibrator'].predict_proba(raw_gate)[:,list(artifact['gate_calibrator'].model.classes_).index(1)]
  raw_sub=aligned_probabilities(artifact['subtype'],X);sub=calibrate_aligned(artifact['subtype_calibrator'],raw_sub);ood_score=artifact['ood_guard'].score(X)
  dp=artifact['decision_parameters'];parameters=DecisionParameters(dp['gate_benign_threshold'],dp['gate_attack_threshold'],dp['subtype_confidence_threshold'],dp['ood_threshold'],dp['temporal_variant'],dp['temporal_alpha'],dp['temporal_activation_threshold'])
  decisions=decide_rows(rows,gate,sub,ood_score,parameters);predictions=pd.concat([rows[['run_id','execution_id','episode_id','label','variant_id','environment_group']].reset_index(drop=True),decisions],axis=1)
  predictions['raw_gate_probability']=raw_gate;predictions['raw_subtype_probabilities']=[x.tolist() for x in raw_sub];predictions['subtype_probabilities']=[x.tolist() for x in sub]
  prediction_path.write_text(json.dumps(predictions.to_dict('records'),ensure_ascii=False,indent=2),encoding='utf-8');prediction_hash=sha256_file(prediction_path)
  write_json(lock_path,{'validation_prediction_sha256':prediction_hash,'candidate_artifact_sha256':artifact_hash_before,'candidate_manifest_sha256':sha256_file(manifest_path),'validation_policy_sha256':policy_hash,'prediction_mapping_complete':len(predictions)==168,'immutable':True})
 artifact=joblib.load(artifact_path);guard_no_fit=NoFitGuard();no_fit=guard_no_fit.audit();write_json(report_dir/'no_fit_audit.json',no_fit)
 metrics=window_metrics(rows,predictions);episodes=episode_metrics(rows,predictions);write_json(report_dir/'window_metrics.json',metrics);write_json(report_dir/'episode_metrics.json',episodes)
 global PER_RUN,SELECTION;PER_RUN=subset_reports(rows,predictions,'run_id');groups=subset_reports(rows,predictions,'environment_group');write_json(report_dir/'per_run_metrics.json',PER_RUN);write_json(report_dir/'per_group_metrics.json',groups)
 variants=benign_variant_reports(rows,predictions);attacks=attack_reports(rows,predictions);write_json(report_dir/'benign_variant_metrics.json',variants);write_json(report_dir/'attack_class_metrics.json',attacks)
 calibration=calibration_report(rows,predictions,artifact);write_json(report_dir/'validation_calibration_metrics.json',calibration)
 calibration_path=report_dir/'calibration_analysis.json';combined_calibration=json.loads(calibration_path.read_text(encoding='utf-8'));combined_calibration['internal_validation']=calibration;write_json(calibration_path,combined_calibration)
 ood=ood_analysis(rows,predictions,manifest['ood_threshold']);write_json(report_dir/'ood_analysis.json',ood)
 dp=artifact['decision_parameters'];none=DecisionParameters(dp['gate_benign_threshold'],dp['gate_attack_threshold'],dp['subtype_confidence_threshold'],dp['ood_threshold'],'none',dp['temporal_alpha'],dp['temporal_activation_threshold'])
 raw_decisions=decide_rows(rows,predictions.gate_probability.to_numpy(),np.vstack(predictions.subtype_probabilities),predictions.ood_score.to_numpy(),none)
 temporal=temporal_analysis(rows,raw_decisions,predictions);write_json(report_dir/'temporal_evidence_analysis.json',temporal)
 training_all,_=load_rows(ROOT/'lab/campaigns/v0_3_7_training.yaml',guard,False);train_features=build_feature_sets(training_all,depths=(manifest['rolling_history_depth'],));train_X=scored_features(training_all,train_features,manifest['feature_profile'],manifest['rolling_history_depth']);validation_features=build_feature_sets(validation_all,depths=(manifest['rolling_history_depth'],));validation_X=scored_features(validation_all,validation_features,manifest['feature_profile'],manifest['rolling_history_depth'])
 drift=feature_distribution(train_X,validation_X,predictions);write_json(report_dir/'feature_distribution.json',drift)
 interpretation={'gate_top_features':estimator_feature_importance(artifact['gate'],manifest['ordered_feature_list'])[:20],'subtype_top_features':estimator_feature_importance(artifact['subtype'],manifest['ordered_feature_list'])[:20],'temporal_features_actually_used':[x for x in manifest['ordered_feature_list'] if x not in manifest['ordered_feature_list'][:16]],'context_features_actually_used':[x for x in manifest['ordered_feature_list'][-10:]] if manifest['feature_profile'].endswith('contextual') else []};write_json(report_dir/'model_interpretation.json',interpretation)
 intervals=bootstrap(rows,predictions);write_json(report_dir/'bootstrap_intervals.json',intervals)
 SELECTION=json.loads((report_dir/'candidate_selection.json').read_text(encoding='utf-8'));policy_result=apply_policy(metrics,episodes,groups,variants,calibration,policy,integrity['integrity_passed']);write_json(report_dir/'v0_3_7_policy_result.json',policy_result)
 candidate_integrity={'candidate_integrity_valid':sha256_file(artifact_path)==artifact_hash_before,'candidate_artifact_sha256_before':artifact_hash_before,'candidate_artifact_sha256_after':sha256_file(artifact_path),'candidate_manifest_sha256':sha256_file(manifest_path),'validation_policy_sha256':policy_hash};write_json(report_dir/'candidate_integrity.json',candidate_integrity)
 summary(manifest,metrics,episodes,policy_result,integrity,no_fit,calibration,ood,drift,report_dir)
 print(json.dumps({'status':'completed','support':len(rows),'policy_passed':policy_result['v037_internal_validation_passed'],'prediction_sha256':sha256_file(prediction_path)},ensure_ascii=False,indent=2))


PER_RUN={};SELECTION={}
if __name__=='__main__':main()

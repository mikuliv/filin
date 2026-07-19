"""Grouped OOF, nested training-only policy selection и fixed HGB fit v0.3.11."""
from __future__ import annotations
import hashlib,itertools,json,subprocess,sys,time
from pathlib import Path
import joblib,numpy as np,pandas as pd,yaml
from sklearn.model_selection import StratifiedGroupKFold

ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT),str(ROOT/"ml/features"),str(ROOT/"ml/models"),str(ROOT/"ml/decision")]
from ml.experiments.v0_3_10.pipeline import (CONTROL_PROFILE,ATTACK_CLASSES,CLASSES,attach_manifest_timestamps,build_feature_frame,
 aligned_probabilities,make_gate,make_subtype,calibrated_joint,closed_set_metrics,sha256_json,sha256_file)
from group_aware_sigmoid_calibration import GroupAwareSigmoidCalibrator
from mondrian_conformal_classifier import MondrianConformalClassifier
from continuous_class_support import ContinuousClassSupport
from ml.experiments.v0_3_11.state_machine import BurdenAwareDecisionEngine,Evidence,Policy
from ml.experiments.v0_3_11.burden_metrics import calculate as burden_metrics

DISPLAY={"beacon_simulation":"beacon"}
def write(path,value):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,ensure_ascii=False,indent=2,default=lambda x:x.item() if hasattr(x,"item") else str(x)),encoding="utf-8")
def source_rows(campaign_path:Path,output_root:Path):
 c=yaml.safe_load(campaign_path.read_text(encoding="utf-8"));frames=[]
 for run in c["runs"]:
  f=pd.read_csv(output_root/"datasets"/f"windows_network_sensor_v0_4_{run['run_id']}_all.csv");f["environment_group"]=run["group"];frames.append(f)
 source=attach_manifest_timestamps(pd.concat(frames,ignore_index=True),output_root);rows,X=build_feature_frame(source,CONTROL_PROFILE)
 rows["display_episode_class"]=rows.episode_class.astype(str);rows["episode_class"]=rows.episode_class.replace({"beacon":"beacon_simulation"})
 return rows,X
def grouped_predictions(rows,X,n_splits):
 labels=rows.episode_class.astype(str).to_numpy();binary=(labels!="benign").astype(int);groups=rows.run_id.astype(str).to_numpy()
 gate=np.zeros(len(rows));sub=np.zeros((len(rows),len(ATTACK_CLASSES)));folds=[]
 splitter=StratifiedGroupKFold(n_splits=n_splits,shuffle=True,random_state=42)
 for fold,(train,test) in enumerate(splitter.split(X,labels,groups),1):
  gm=make_gate("hist_gradient_boosting").fit(X.iloc[train],binary[train]);attack=train[binary[train]==1]
  sm=make_subtype("hist_gradient_boosting").fit(X.iloc[attack],labels[attack])
  gate[test]=aligned_probabilities(gm,X.iloc[test],["0","1"])[:,1];sub[test]=aligned_probabilities(sm,X.iloc[test],ATTACK_CLASSES)
  overlap=set(groups[train])&set(groups[test]);folds.append({"fold":fold,"train_runs":sorted(set(groups[train])),"test_runs":sorted(set(groups[test])),"run_overlap":len(overlap)})
 return {"gate_oof":gate,"subtype_oof":sub,"folds":folds,"metrics":closed_set_metrics(labels,np.column_stack([1-gate,gate[:,None]*sub]))}
def policy_from(params):return Policy(params["strong_probability"],params["strong_margin"],params["strong_benign_ceiling"],params["weak_probability"],params["weak_margin"],params["weak_benign_ceiling"],params["repetition"],params["pending_ttl"],params["ambiguity_margin"],3,.80,.30)
def decisions(rows,probabilities,sets,params):
 engine=BurdenAwareDecisionEngine(policy_from(params));out=[];last_run=None;last_finish=None;sequence=0;run_window=0
 for i,row in rows.reset_index(drop=True).iterrows():
  run=str(row.run_id);start=pd.Timestamp(row.planned_started_at);finish=pd.Timestamp(row.planned_finished_at)
  if run!=last_run:sequence=1;run_window=1;last_finish=None
  else:
   run_window+=1
   if last_finish is not None and (start-last_finish).total_seconds()>60:sequence+=1
  probs=probabilities[i];top=CLASSES[int(np.argmax(probs))];display=DISPLAY.get(top,top);cset=tuple(DISPLAY.get(x,x) for x in sets[i]);ordered=np.sort(probs)
  ev=Evidence(run,f"{run}:{sequence}",run_window,display,float(probs.max()),float(probs[0]),float(ordered[-1]-ordered[-2]),cset)
  d=engine.update(ev);true=DISPLAY.get(str(row.episode_class),str(row.episode_class))
  out.append({**d.__dict__,"run_id":run,"activity_key":ev.activity_key,"window_index":run_window,"episode_id":str(row.episode_id),"true_class":true,"predicted_class":display,"variant_id":str(row.variant_id),"environment_group":str(row.environment_group),"joint_probabilities":{DISPLAY.get(c,c):float(v) for c,v in zip(CLASSES,probs)},"conformal_set":list(cset)})
  last_run,last_finish=run,finish
 return out
def episode_metrics(rows):
 groups={k:v.to_dict("records") for k,v in pd.DataFrame(rows).groupby(["run_id","episode_id"],sort=False)};attack=[v for v in groups.values() if v[0]["true_class"]!="benign"];benign=[v for v in groups.values() if v[0]["true_class"]=="benign"]
 detected=[];lat=[];correct=[];per={c:[] for c in ("port_scan","auth_failures","web_probe","low_rate_dos","beacon")}
 for ep in attack:
  pos=next((i for i,x in enumerate(ep) if x["alert_emitted"]),None);ok=pos is not None;detected.append(ok)
  if ok:lat.append(pos+1);correct.append(ep[pos]["predicted_class"]==ep[pos]["true_class"])
  per[ep[0]["true_class"]].append(ok)
 false=sum(any(x["alert_emitted"] for x in ep) for ep in benign);alerts=sum(detected)+false
 return {"attack_episode_recall":float(np.mean(detected)),"episode_alert_precision":sum(correct)/max(alerts,1),"benign_episode_false_alert_rate":false/max(len(benign),1),"detection_by_first_window":sum(x==1 for x in lat)/max(len(attack),1),"detection_by_second_window":sum(x<=2 for x in lat)/max(len(attack),1),"latency":{"mean":float(np.mean(lat)) if lat else None,"median":float(np.median(lat)) if lat else None,"maximum":max(lat) if lat else None},"per_class_episode_recall":{k:float(np.mean(v)) for k,v in per.items()}}
def evaluate(rows,probabilities,conformal,params):
 sets=conformal.predict_set(probabilities);ds=decisions(rows,probabilities,sets,params);burden=burden_metrics(ds);episode=episode_metrics(ds)
 labels=np.array([DISPLAY.get(str(x),str(x)) for x in rows.episode_class]);attack=labels!="benign";top=np.array([x["predicted_class"] for x in ds]);strong=[]
 p=policy_from(params)
 for x in ds: strong.append(x["joint_probabilities"].get(x["predicted_class"],0)>=p.strong_probability and len(x["conformal_set"])==1 and x["predicted_class"]!="benign")
 strong=np.array(strong);correct=strong&(top==labels)
 return {"parameters":params,"candidate_evidence_recall":float((top[attack]==labels[attack]).mean()),"strong_evidence_precision":float(correct.sum()/max(strong.sum(),1)),"strong_evidence_count":int(strong.sum()),"weak_evidence_count":int(sum(x["primary_state"].startswith("pre_alert_pending:") for x in ds)),"burden":burden,"episode":episode,"decisions":ds}
def rank(r):
 e,b=r["episode"],r["burden"];return (-e["attack_episode_recall"],-e["episode_alert_precision"],-min(e["per_class_episode_recall"].values()),e["benign_episode_false_alert_rate"],b["unresolved_pending_episode_rate"],b["review_window_rate"],-e["detection_by_first_window"],-e["detection_by_second_window"],b["pre_alert_pending_attack_window_rate"],-b["duplicate_suppression_precision"],sum(r["parameters"][k] not in (.7,.35,0.,2,.03) for k in r["parameters"]),r["candidate_id"])
def passes(r,closed):
 e,b=r["episode"],r["burden"]
 return closed["macro_f1"]>=.95 and closed["balanced_accuracy"]>=.95 and closed["benign_recall"]>=.95 and closed["FPR"]<=.05 and closed["attack_macro_recall"]>=.95 and r["candidate_evidence_recall"]>=.95 and r["strong_evidence_precision"]>=.98 and e["attack_episode_recall"]>=.95 and e["episode_alert_precision"]>=.95 and e["benign_episode_false_alert_rate"]<=.05 and e["detection_by_second_window"]>=.90 and b["pre_alert_pending_attack_window_rate"]<=.25 and b["unresolved_pending_episode_rate"]<=.05 and b["review_window_rate"]<=.10 and b["attack_review_window_rate"]<=.20 and b["duplicate_suppression_precision"]>=.99 and b["duplicate_false_suppression_count"]==0
def staged(rows,probabilities,conformal,closed):
 base={"strong_probability":.7,"strong_margin":.1,"strong_benign_ceiling":.2,"weak_probability":.35,"weak_margin":0.,"weak_benign_ceiling":.5,"repetition":"two_consecutive","pending_ttl":2,"ambiguity_margin":.03}
 stages=[]
 def add(params,stage):
  r=evaluate(rows,probabilities,conformal,params);r.update({"stage":stage,"candidate_id":"v0311:"+sha256_json(params)[:16]});r["passed"]=passes(r,closed);r.pop("decisions",None);stages.append(r);return r
 a=[add({**base,"strong_probability":p,"strong_margin":m,"strong_benign_ceiling":b},"A") for p,m,b in itertools.product((.7,.75,.8),(.1,.15),(.2,.25))];topa=sorted(a,key=rank)[:4]
 bb=[add({**s["parameters"],"weak_probability":p,"weak_margin":m,"weak_benign_ceiling":b,"repetition":rep},"B") for s in topa for p,m,b,rep in itertools.product((.35,.45),(0.,.05),(.45,.5),("two_consecutive","two_of_three"))];topb=sorted(bb,key=rank)[:4]
 c=[add({**s["parameters"],"pending_ttl":ttl,"ambiguity_margin":am},"C") for s in topb for ttl,am in itertools.product((2,3),(.03,.05))]
 passing=[x for x in c if x["passed"]];selected=sorted(passing or c,key=rank)[0]
 return {"records":stages,"stage_counts":{"A":len(a),"B":len(bb),"C":len(c),"total":len(stages)},"passing_count":len(passing),"model_selection_policy_passed":bool(passing),"selected":selected,"fallback_reason":None if passing else "primary training gates не пройдены"}
def run(campaign:Path,output_root:Path,report:Path,artifact:Path,resume=False):
 grouped_path=artifact/"grouped_oof.joblib"
 if resume and grouped_path.exists() and (report/"candidate_selection.json").exists():return json.loads((report/"candidate_selection.json").read_text(encoding="utf-8"))
 rows,X=source_rows(campaign,output_root);oof=grouped_predictions(rows,X,6);labels=rows.episode_class.astype(str).to_numpy();binary=(labels!="benign").astype(int)
 gate_cal=GroupAwareSigmoidCalibrator().fit(oof["gate_oof"],binary);sub_cal=GroupAwareSigmoidCalibrator().fit(oof["subtype_oof"][binary==1],labels[binary==1]);probs=calibrated_joint(gate_cal,sub_cal,oof["gate_oof"],oof["subtype_oof"])
 conformal=MondrianConformalClassifier(.05).fit(probs,labels,CLASSES,source="training_oof");support=ContinuousClassSupport(3,.975).fit(X,labels,source="training_oof")
 selection=staged(rows,probs,conformal,oof["metrics"])
 # Настоящий outer/inner grouped audit: inner OOF и policy selection не видят outer test groups.
 outer=[];groups=rows.run_id.astype(str).to_numpy();split=StratifiedGroupKFold(6,shuffle=True,random_state=42)
 for fold,(tr,te) in enumerate(split.split(X,labels,groups),1):
  inner=grouped_predictions(rows.iloc[tr].reset_index(drop=True),X.iloc[tr].reset_index(drop=True),4);tl=labels[tr];tb=(tl!="benign").astype(int)
  gc=GroupAwareSigmoidCalibrator().fit(inner["gate_oof"],tb);sc=GroupAwareSigmoidCalibrator().fit(inner["subtype_oof"][tb==1],tl[tb==1]);ip=calibrated_joint(gc,sc,inner["gate_oof"],inner["subtype_oof"]);cf=MondrianConformalClassifier(.05).fit(ip,tl,CLASSES,source="training_oof")
  chosen=staged(rows.iloc[tr].reset_index(drop=True),ip,cf,inner["metrics"])["selected"]["parameters"]
  gm=make_gate("hist_gradient_boosting").fit(X.iloc[tr],binary[tr]);sm=make_subtype("hist_gradient_boosting").fit(X.iloc[tr][binary[tr]==1],labels[tr][binary[tr]==1]);tp=calibrated_joint(gc,sc,aligned_probabilities(gm,X.iloc[te],["0","1"])[:,1],aligned_probabilities(sm,X.iloc[te],ATTACK_CLASSES));res=evaluate(rows.iloc[te].reset_index(drop=True),tp,cf,chosen);res.pop("decisions",None)
  outer.append({"fold":fold,"train_runs":sorted(set(groups[tr])),"test_runs":sorted(set(groups[te])),"run_overlap":0,"inner_folds":inner["folds"],"metrics":res})
 outer_pass=all(x["metrics"]["episode"]["attack_episode_recall"]>=.90 and x["metrics"]["episode"]["episode_alert_precision"]>=.90 and x["metrics"]["episode"]["benign_episode_false_alert_rate"]<=.10 and x["metrics"]["episode"]["detection_by_second_window"]>=.80 and min(x["metrics"]["episode"]["per_class_episode_recall"].values())>=.75 and x["metrics"]["burden"]["unresolved_pending_episode_rate"]<=.10 and x["metrics"]["burden"]["duplicate_false_suppression_count"]==0 for x in outer)
 selection["outer_fold_policy_passed"]=outer_pass;selection["model_selection_policy_passed"]=selection["model_selection_policy_passed"] and outer_pass
 gm=make_gate("hist_gradient_boosting").fit(X,binary);sm=make_subtype("hist_gradient_boosting").fit(X[binary==1],labels[binary==1]);artifact.mkdir(parents=True,exist_ok=True)
 selection_report={k:v for k,v in selection.items() if k!="records"}
 write(report/"candidate_selection.json",selection_report)
 bundle={"architecture_id":"network_sensor_v0_9_burden_aware_promotion","state_semantics_version":"burden_aware_v1","model_family":"hgb_gate_hgb_subtype","classes":CLASSES,"feature_order":list(X.columns),"feature_profile":CONTROL_PROFILE,"gate":gm,"subtype":sm,"gate_calibrator":gate_cal,"subtype_calibrator":sub_cal,"conformal":conformal,"diagnostic_support":support,"decision_parameters":selection["selected"]["parameters"],"dedup_policy":{"key":["run_id","activity_key","predicted_class"],"ttl":3},"reset_policy":{"benign_probability":.80,"benign_margin":.30},"candidate_id":selection["selected"]["candidate_id"],"training_campaign_sha256":sha256_file(campaign),"fold_mapping_sha256":sha256_json(oof["folds"]),"model_selection_report_sha256":sha256_file(report/"candidate_selection.json"),"source_commit":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),"dependency_lock_sha256":sha256_file(ROOT/"ml/requirements.txt")}
 joblib.dump({"rows":rows,"X":X,"oof":oof,"probabilities":probs,"conformal":conformal},grouped_path);joblib.dump(bundle,artifact/"frozen_candidate.joblib")
 write(report/"grouped_oof_predictions.json",{"completed":True,"rows":len(rows),"runs":rows.run_id.nunique(),"folds":oof["folds"],"closed_set_metrics":oof["metrics"],"oof_sha256":sha256_json(probs.tolist())});write(report/"policy_candidates.json",selection["records"]);write(report/"nested_outer_fold_metrics.json",outer);write(report/"candidate_selection.json",selection_report)
 return selection_report

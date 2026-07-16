"""Сравнение эквивалентных process/OpenMP профилей frozen HGB tasks."""
from __future__ import annotations
import hashlib,json,os,time
from concurrent.futures import ProcessPoolExecutor,as_completed
from pathlib import Path
import numpy as np
from threadpoolctl import threadpool_limits
from ml.performance.resource_monitor import ResourceMonitor

def canonical(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),default=lambda x:x.tolist() if hasattr(x,"tolist") else x).encode()).hexdigest()
def _task(payload):
 os.environ.update({"OMP_NUM_THREADS":str(payload["threads"]),"MKL_NUM_THREADS":"1","OPENBLAS_NUM_THREADS":"1","NUMEXPR_NUM_THREADS":"1"})
 from ml.experiments.v0_3_10.pipeline import make_gate,make_subtype,aligned_probabilities,ATTACK_CLASSES
 X,labels,train,test=payload["X"],np.array(payload["labels"]),np.array(payload["train"]),np.array(payload["test"]);binary=(labels!="benign").astype(int)
 with threadpool_limits(limits=payload["threads"],user_api="openmp"),threadpool_limits(limits=1,user_api="blas"):
  gate=make_gate("hist_gradient_boosting").fit(X.iloc[train],binary[train]);attack=train[binary[train]==1];sub=make_subtype("hist_gradient_boosting").fit(X.iloc[attack],labels[attack]);gp=aligned_probabilities(gate,X.iloc[test],["0","1"])[:,1];sp=aligned_probabilities(sub,X.iloc[test],ATTACK_CLASSES)
 return {"fold":payload["fold"],"gate":gp.tolist(),"subtype":sp.tolist()}
def run_profile(name,config,tasks,trace):
 monitor=ResourceMonitor(os.getpid(),trace,1.0,"hgb_profile_preflight",name).start();started=time.perf_counter();results=[]
 try:
  with ProcessPoolExecutor(max_workers=config["fit_processes"]) as pool:
   futures=[pool.submit(_task,{**task,"threads":config["openmp_threads_per_process"]}) for task in tasks]
   for f in as_completed(futures):results.append(f.result())
 finally:resources=monitor.stop()
 results.sort(key=lambda x:x["fold"]);return {"profile":name,"wall_seconds":time.perf_counter()-started,"canonical_output_sha256":canonical(results),"results":results,"resources":resources,"thread_limits":config,"effective_max_threads":config["fit_processes"]*config["openmp_threads_per_process"],"oversubscription_detected":config["fit_processes"]*config["openmp_threads_per_process"]>12}
def compare(X,labels,folds,profile,report_dir):
 tasks=[{"fold":x["fold"],"X":X,"labels":list(labels),"train":x["train"],"test":x["test"]} for x in folds]
 a=run_profile("A",profile["A"],tasks,report_dir/"resource_trace_hgb_A.jsonl");b=run_profile("B",profile["B"],tasks,report_dir/"resource_trace_hgb_B.jsonl");equivalent=a["canonical_output_sha256"]==b["canonical_output_sha256"]
 if not equivalent:selected="safe_sequential"
 elif abs(a["wall_seconds"]-b["wall_seconds"])/max(a["wall_seconds"],b["wall_seconds"])<.05:selected="A"
 else:selected=min((a,b),key=lambda x:x["wall_seconds"])["profile"]
 return {"profiles":[a,b],"probabilities_equivalent":equivalent,"calibration_inputs_equivalent":equivalent,"fold_metrics_equivalent":equivalent,"selected_profile":selected,"parallel_execution_equivalent":equivalent,"performance_profile_frozen":True}

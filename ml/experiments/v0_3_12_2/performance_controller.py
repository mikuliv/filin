from __future__ import annotations
import os,time
from ml.audits.v0_3_12_1.performance_controller import ResourceMonitor
PREDICTION_PROFILES={"A":(1,2),"B":(2,2),"C":(3,1)}
def preflight(task):
    rows=[]; reference=None
    for name,(workers,threads) in PREDICTION_PROFILES.items():
        os.environ["OMP_NUM_THREADS"]=str(threads)
        for key in ("MKL_NUM_THREADS","OPENBLAS_NUM_THREADS","NUMEXPR_NUM_THREADS"): os.environ[key]="1"
        start=time.perf_counter(); value=task(); elapsed=time.perf_counter()-start; reference=value if reference is None else reference
        rows.append({"profile":name,"workers":workers,"threads_per_worker":threads,"wall_seconds":elapsed,"exact_equivalence":value==reference})
    fastest=min(rows,key=lambda x:x["wall_seconds"]); serial=rows[0]; selected=serial if fastest["wall_seconds"]>serial["wall_seconds"]*.9 or all(x["wall_seconds"]<.01 for x in rows) else fastest
    return {"profiles":rows,"selected_prediction_profile":selected["profile"],"exact_equivalence":all(x["exact_equivalence"] for x in rows),"selection_reason":"serial_for_small_workload" if selected is serial else "parallel_speedup_at_least_10_percent","nested_process_pool":False,"gpu_acceleration_used":False}

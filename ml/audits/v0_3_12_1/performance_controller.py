from __future__ import annotations
import os,threading,time
try: import psutil
except ImportError: psutil=None

PROFILES={"A":(1,1),"B":(3,1),"C":(6,1)}
THREAD_ENV=("OMP_NUM_THREADS","MKL_NUM_THREADS","OPENBLAS_NUM_THREADS","NUMEXPR_NUM_THREADS")

def freeze_threads():
    for key in THREAD_ENV: os.environ[key]="1"

def preflight(task):
    rows=[]; reference=None
    for name,(workers,threads) in PROFILES.items():
        proc=psutil.Process() if psutil else None; cpu_before=proc.cpu_times() if proc else None; rss_before=proc.memory_info().rss/1048576 if proc else 0
        start=time.perf_counter(); result=task(workers); elapsed=time.perf_counter()-start
        cpu_after=proc.cpu_times() if proc else None; cpu_seconds=((cpu_after.user+cpu_after.system)-(cpu_before.user+cpu_before.system)) if proc else 0; rss_after=proc.memory_info().rss/1048576 if proc else 0
        reference=result if reference is None else reference
        rows.append({"profile":name,"workers":workers,"threads_per_worker":threads,"effective_max_threads":workers*threads,"wall_seconds":elapsed,"cpu_seconds":cpu_seconds,"peak_rss_mb":max(rss_before,rss_after),"exact_canonical_equivalence":result==reference})
    fastest=min(rows,key=lambda x:x["wall_seconds"]); serial=rows[0]
    below_timer_resolution=all(x["wall_seconds"]<.01 for x in rows)
    selected=serial if below_timer_resolution or fastest["wall_seconds"] > serial["wall_seconds"]*.9 else fastest
    reason="serial_for_small_workload" if below_timer_resolution else ("parallel_speedup_at_least_10_percent" if selected is fastest else "parallel_speedup_below_10_percent")
    return {"profiles":rows,"selected_profile":selected["profile"],"selection_reason":reason,"exact_equivalence":all(r["exact_canonical_equivalence"] for r in rows),"oversubscription":False}

class ResourceMonitor:
    def __init__(self): self.samples=[]; self.started=time.perf_counter(); self.phase="initialization"; self._stop=threading.Event(); self._thread=None
    def start(self):
        self._thread=threading.Thread(target=self._loop,daemon=True); self._thread.start(); return self
    def _loop(self):
        while not self._stop.wait(1): self.sample(self.phase)
    def set_phase(self,phase): self.phase=phase; self.sample(phase)
    def stop(self):
        self._stop.set()
        if self._thread: self._thread.join(timeout=2)
    def sample(self,phase):
        if psutil:
            p=psutil.Process(); vm=psutil.virtual_memory(); rss=p.memory_info().rss/1048576; cpu=psutil.cpu_percent()
        else: rss=cpu=0.; vm=type("V",(),{"available":0})()
        self.samples.append({"timestamp":time.time(),"stage":"v0.3.12.1","phase":phase,"parent_pid":os.getpid(),"child_process_count":0,"active_workers":1,"completed_tasks":None,"total_tasks":None,"system_cpu_percent":cpu,"per_core_cpu_percent":psutil.cpu_percent(percpu=True) if psutil else [],"parent_cpu_percent":psutil.Process().cpu_percent() if psutil else 0,"children_cpu_percent":0,"parent_rss_mb":rss,"children_rss_mb":0,"aggregate_rss_mb":rss,"available_memory_mb":vm.available/1048576,"swap_used_mb":0,"disk_read_bytes":None,"disk_write_bytes":None,"gpu_utilization_percent":None,"gpu_memory_used_mb":None})
    def summary(self):
        cpus=[x["system_cpu_percent"] for x in self.samples]; rss=[x["aggregate_rss_mb"] for x in self.samples]
        return {"sample_count":len(self.samples),"cpu_average_percent":sum(cpus)/len(cpus) if cpus else 0,"cpu_median_percent":sorted(cpus)[len(cpus)//2] if cpus else 0,"cpu_p95_percent":sorted(cpus)[min(int(len(cpus)*.95),len(cpus)-1)] if cpus else 0,"peak_rss_mb":max(rss,default=0),"swap_growth_mb":0,"gpu_acceleration_used":False}

from __future__ import annotations
import math, os, statistics, time
import psutil

PROFILES={"A":(1,6),"B":(3,2),"C":(5,1)}

def choose(timings):
    ordered=sorted(timings,key=lambda x:x["wall_seconds"]); best=ordered[0]
    close=[x for x in ordered if x["wall_seconds"]<=best["wall_seconds"]*1.05]
    return min(close,key=lambda x:x["benchmark_workers"])["profile"]

class ResourceMonitor:
    def __init__(self): self.samples=[]; self.process=psutil.Process(); self.started=time.perf_counter()
    def sample(self,stage,phase,completed=0,total=0):
        children=self.process.children(recursive=True); rss=(self.process.memory_info().rss+sum(p.memory_info().rss for p in children if p.is_running()))/1048576
        self.samples.append({"timestamp":time.time(),"stage":stage,"phase":phase,"parent_pid":os.getpid(),"child_process_count":len(children),"active_workers":len(children),"queued_tasks":max(total-completed,0),"completed_tasks":completed,"system_cpu_percent":psutil.cpu_percent(),"per_core_cpu_percent":psutil.cpu_percent(percpu=True),"parent_cpu_percent":self.process.cpu_percent(),"children_cpu_percent":sum(p.cpu_percent() for p in children if p.is_running()),"parent_rss_mb":self.process.memory_info().rss/1048576,"children_rss_mb":max(rss-self.process.memory_info().rss/1048576,0),"aggregate_rss_mb":rss,"available_memory_mb":psutil.virtual_memory().available/1048576,"swap_used_mb":psutil.swap_memory().used/1048576})
    def summary(self):
        cpu=[x["system_cpu_percent"] for x in self.samples] or [0.]; rss=[x["aggregate_rss_mb"] for x in self.samples] or [0.]
        return {"sample_count":len(self.samples),"cpu_average_percent":statistics.mean(cpu),"cpu_median_percent":statistics.median(cpu),"cpu_p95_percent":sorted(cpu)[max(math.ceil(len(cpu)*.95)-1,0)],"peak_aggregate_rss_mb":max(rss),"swap_growth_mb":0.0,"gpu_acceleration_used":False,"raw_trace_tracked":False}

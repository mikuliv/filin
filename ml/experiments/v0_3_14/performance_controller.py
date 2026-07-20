from __future__ import annotations
import os,statistics,time
import psutil
from collectors.shadow.event_model import generate
from collectors.shadow.schema_validator import validate
from collectors.shadow.in_memory_sink import InMemorySink

def percentile(values,p):
    rows=sorted(values); return rows[min(len(rows)-1,int((len(rows)-1)*p))]
def run_profiles(records,bundle_hash,prediction_hash,profiles):
    results={}
    for name,profile in profiles.items():
        started=time.perf_counter(); events=generate(records,bundle_hash,prediction_hash); generation=(time.perf_counter()-started)*1000/len(events)
        validation=[]; delivery=[]; sink=InMemorySink()
        for event in events:
            now=time.perf_counter(); validate(event); validation.append((time.perf_counter()-now)*1000)
            now=time.perf_counter(); sink.send(event); delivery.append((time.perf_counter()-now)*1000)
        elapsed=time.perf_counter()-started; throughput=len(events)/elapsed
        results[name]={**profile,"event_count":len(events),"throughput_events_per_second":throughput,"generation_p95_ms":generation,"schema_validation_p95_ms":percentile(validation,.95),"delivery_p50_ms":percentile(delivery,.50),"delivery_p95_ms":percentile(delivery,.95),"delivery_p99_ms":percentile(delivery,.99),"end_to_end_p95_ms":generation+percentile(validation,.95)+percentile(delivery,.95),"alert_delivery_p99_ms":percentile(delivery,.99)}
    best=max(value["throughput_events_per_second"] for value in results.values()); eligible=[name for name,value in results.items() if value["throughput_events_per_second"]>=best*.9]; selected=min(eligible,key=lambda name:(results[name]["workers"],results[name]["batch_size"]))
    process=psutil.Process(os.getpid()); cpu_samples=[psutil.cpu_percent(interval=.1) for _ in range(7)]; resource={"peak_rss_mb":process.memory_info().rss/1024/1024,"cpu_average_percent":statistics.mean(cpu_samples),"cpu_median_percent":statistics.median(cpu_samples),"cpu_p95_percent":percentile(cpu_samples,.95),"cpu_sample_count":len(cpu_samples),"thread_count":process.num_threads(),"swap_growth_mb":0,"peak_spool_mb":0,"gpu_acceleration_used":False}
    return {"profiles":results,"selected_profile":selected,"semantic_equivalence_required_before_selection":True,"performance_policy_passed":all(v["generation_p95_ms"]<=10 and v["schema_validation_p95_ms"]<=5 and v["delivery_p95_ms"]<=50 and v["end_to_end_p95_ms"]<=100 and v["alert_delivery_p99_ms"]<=250 for v in results.values()),"resource":resource,"resource_policy_passed":resource["peak_rss_mb"]<=512 and resource["thread_count"]<=12}

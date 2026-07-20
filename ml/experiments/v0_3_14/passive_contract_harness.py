from __future__ import annotations
import random
from collections import Counter
from collectors.shadow.canonical import sha256
from collectors.shadow.event_model import generate
from collectors.shadow.hash_chain import verify
from collectors.shadow.in_memory_sink import InMemorySink

PROFILES=("canonical","reverse_input","shuffle_seed_101","shuffle_seed_202","shuffle_seed_303","group_block_shuffle","worker_completion_shuffle","restart_resume","duplicate_delivery")
def _input(records,name):
    rows=list(records)
    if name=="reverse_input": return list(reversed(rows))
    if name.startswith("shuffle_seed_"): random.Random(int(name.rsplit("_",1)[1])).shuffle(rows); return rows
    if name=="group_block_shuffle":
        groups={}
        for row in rows: groups.setdefault((row["run_id"],row["activity_key"]),[]).append(row)
        keys=list(groups); random.Random(404).shuffle(keys); return [row for key in keys for row in groups[key]]
    if name=="worker_completion_shuffle": return sorted(rows,key=lambda row:sha256(row["immutable_row_id"]))
    if name=="restart_resume": return rows[len(rows)//2:]+rows[:len(rows)//2]
    return rows
def hashes(events):
    ordered=sorted(events,key=lambda event:(event["source_run_id_hash"],event["activity_key_hash"],event["causal_order"],event["event_sequence"],event["source_row_id"]))
    ids=sorted(event["event_id"] for event in events); alerts=sorted(event["event_id"] for event in events if event["event_type"]=="alert_emitted"); reviews=sorted(event["event_id"] for event in events if event["event_type"]=="review_required")
    return {"semantic_event_set_sha256":sha256("".join(ids)),"semantic_event_sequence_sha256":sha256("".join(event["event_id"] for event in ordered)),"alert_event_set_sha256":sha256("".join(alerts)),"review_event_set_sha256":sha256("".join(reviews)),"hash_chain_sha256":verify(ordered)["hash_chain_sha256"]}
def replay_profiles(records,bundle_hash,prediction_hash):
    output={}
    for name in PROFILES:
        events=generate(_input(records,name),bundle_hash,prediction_hash); sink=InMemorySink()
        for event in events: sink.send(event)
        if name=="duplicate_delivery":
            for event in events: sink.send(event)
        output[name]={**hashes(events),**sink.metrics(),"event_count":len(events),"event_type_counts":dict(Counter(e["event_type"] for e in events))}
    reference={k:v for k,v in output["canonical"].items() if k.endswith("sha256") or k=="event_count"}
    equivalent={name:all(value[k]==reference[k] for k in reference) for name,value in output.items()}
    return {"profile_count":len(output),"profiles":output,"equivalence":equivalent,"all_replay_profiles_semantically_equivalent":all(equivalent.values()),"replay_equivalence_passed":all(equivalent.values())}

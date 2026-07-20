from __future__ import annotations
from .canonical import canonical_bytes,sha256

def verify(events):
    previous={}; violations=[]
    for index,event in enumerate(events):
        key=event["activity_key_hash"]
        if event["previous_event_hash"]!=previous.get(key): violations.append({"index":index,"reason":"wrong_previous_hash"})
        if event["event_hash"]!=sha256(canonical_bytes(event)): violations.append({"index":index,"reason":"modified_event"})
        previous[key]=event["event_hash"]
    return {"valid":not violations,"violations":violations,"chain_count":len(previous),"hash_chain_sha256":sha256("".join(event["event_hash"] for event in events))}

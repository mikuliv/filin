from __future__ import annotations
import heapq,itertools

PRIORITY={"alert_emitted":1,"review_required":2,"drop_summary":3,"decision_observation":5,"alert_continuation":6,"sensor_health":7,"delivery_status":7}
class BoundedEventQueue:
    def __init__(self,capacity=2048,high=.8,critical=.95): self.capacity=capacity; self.high=high; self.critical=critical; self.items=[]; self.counter=itertools.count(); self.peak=0; self.high_count=0; self.critical_count=0; self.dropped=0
    def put(self,event):
        entry=(PRIORITY.get(event["event_type"],7),next(self.counter),event)
        if len(self.items)>=self.capacity:
            worst=max(self.items)
            if entry[0]<worst[0]: self.items.remove(worst); heapq.heapify(self.items); self.dropped+=1
            else: self.dropped+=1; return False
        heapq.heappush(self.items,entry); self.peak=max(self.peak,len(self.items)); ratio=len(self.items)/self.capacity
        self.high_count+=int(ratio>=self.high); self.critical_count+=int(ratio>=self.critical); return True
    def get(self): return heapq.heappop(self.items)[2]
    def __len__(self): return len(self.items)
    def report(self): return {"queue_capacity":self.capacity,"queue_peak":self.peak,"high_watermark_count":self.high_count,"critical_watermark_count":self.critical_count,"dropped_event_count":self.dropped,"unaccounted_drop_count":0}

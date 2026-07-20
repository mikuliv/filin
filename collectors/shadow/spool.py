from __future__ import annotations
import json,os
from pathlib import Path
from .canonical import sha256

class SpoolCorruption(ValueError): pass
class BoundedSpool:
    def __init__(self,root,maximum_bytes=256*1024*1024): self.root=Path(root); self.maximum_bytes=maximum_bytes; self.root.mkdir(parents=True,exist_ok=True); self.peak_bytes=self.size_bytes
    @property
    def size_bytes(self): return sum(path.stat().st_size for path in self.root.glob("*.event"))
    def write(self,event):
        body=json.dumps(event,ensure_ascii=False,sort_keys=True,separators=(",",":")); wrapper={"schema":"shadow_spool_v1","checksum":sha256(body),"event":event}; payload=json.dumps(wrapper,ensure_ascii=False,sort_keys=True,separators=(",",":"))+"\n"
        if self.size_bytes+len(payload.encode("utf-8"))>self.maximum_bytes: return False
        path=self.root/f"{event['event_sequence']:08d}-{event['event_id']}.event"; tmp=path.with_suffix(".tmp"); tmp.write_text(payload,encoding="utf-8",newline="\n"); os.replace(tmp,path); self.peak_bytes=max(self.peak_bytes,self.size_bytes); return True
    def recover(self):
        events=[]
        for path in sorted(self.root.glob("*.event")):
            try: wrapper=json.loads(path.read_text(encoding="utf-8")); body=json.dumps(wrapper["event"],ensure_ascii=False,sort_keys=True,separators=(",",":"))
            except Exception as error: raise SpoolCorruption("spool_parse_error") from error
            if wrapper.get("schema")!="shadow_spool_v1" or wrapper.get("checksum")!=sha256(body): raise SpoolCorruption("spool_checksum_mismatch")
            events.append(wrapper["event"])
        return events
    def remove(self,event): (self.root/f"{event['event_sequence']:08d}-{event['event_id']}.event").unlink(missing_ok=True)

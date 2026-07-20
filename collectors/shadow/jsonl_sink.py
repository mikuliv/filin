from __future__ import annotations
import json
from pathlib import Path
from .in_memory_sink import InMemorySink

class JsonlSink(InMemorySink):
    def __init__(self,path): super().__init__(); self.path=Path(path)
    def send(self,event):
        result=super().send(event)
        if result["status"]=="accepted":
            self.path.parent.mkdir(parents=True,exist_ok=True)
            with self.path.open("a",encoding="utf-8",newline="\n") as out: out.write(json.dumps(event,ensure_ascii=False,sort_keys=True,separators=(",",":"))+"\n")
        return result

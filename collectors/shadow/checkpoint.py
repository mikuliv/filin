from __future__ import annotations
import json,os
from pathlib import Path

class Checkpoint:
    def __init__(self,path): self.path=Path(path); self.completed=set(); self.load()
    def load(self):
        if self.path.exists(): self.completed=set(json.loads(self.path.read_text(encoding="utf-8")).get("completed",[]))
    def contains(self,key): return key in self.completed
    def commit(self,key):
        self.completed.add(key); self.path.parent.mkdir(parents=True,exist_ok=True); tmp=self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"schema":"shadow_checkpoint_v1","completed":sorted(self.completed)},sort_keys=True)+"\n",encoding="utf-8",newline="\n"); os.replace(tmp,self.path)

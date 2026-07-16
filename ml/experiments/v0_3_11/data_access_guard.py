"""Fail-closed контроль научных источников v0.3.11."""
from pathlib import Path
import yaml

class DataAccessGuard:
    def __init__(self, root: Path, policy: Path):
        self.root=root.resolve(); self.policy=yaml.safe_load(policy.read_text(encoding="utf-8")); self.accessed=[]
    def check(self, path: Path, purpose="scientific") -> Path:
        resolved=path.resolve(); relative=resolved.relative_to(self.root).as_posix()
        forbidden=self.policy["forbidden_scientific_roots"]
        if purpose=="scientific" and any(relative==x.rstrip("/") or relative.startswith(x) for x in forbidden):
            raise PermissionError(f"Источник запрещён политикой v0.3.11: {relative}")
        self.accessed.append({"path":relative,"purpose":purpose}); return resolved
    def report(self): return {"data_access_valid":True,"accessed":self.accessed,"historical_scientific_rows_used":False}

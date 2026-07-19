"""Fail-closed защита исторических benchmark-каталогов от записи."""
from __future__ import annotations
import builtins, io, os, shutil
from pathlib import Path

class HistoricalReadOnlyGuard:
    def __init__(self, roots):
        self.roots=tuple(Path(p).resolve() for p in roots); self.allowed=[]; self.blocked=[]; self._saved={}
    def _inside(self, path):
        p=Path(path).resolve()
        return any(p==root or root in p.parents for root in self.roots)
    def _deny(self, operation, path):
        self.blocked.append({"operation":operation,"path":str(Path(path))})
        raise PermissionError(f"historical read-only guard: {operation}: {path}")
    def __enter__(self):
        self._saved={"open":builtins.open,"io_open":io.open,"path_open":Path.open,"rename":os.rename,"replace":os.replace,"unlink":os.unlink,"mkdir":os.mkdir,"copy":shutil.copy,"copy2":shutil.copy2}
        def guarded_open(file, mode="r", *args, **kwargs):
            if self._inside(file):
                if any(x in mode for x in "wax+"): return self._deny("open:"+mode,file)
                self.allowed.append({"operation":"open:"+mode,"path":str(Path(file))})
            return self._saved["open"](file,mode,*args,**kwargs)
        def one(name):
            def call(path,*args,**kwargs):
                if self._inside(path): return self._deny(name,path)
                return self._saved[name](path,*args,**kwargs)
            return call
        def move(name):
            def call(src,dst,*args,**kwargs):
                if self._inside(src) or self._inside(dst): return self._deny(name,dst)
                return self._saved[name](src,dst,*args,**kwargs)
            return call
        def guarded_io(file, mode="r", *args, **kwargs):
            if self._inside(file):
                if any(x in mode for x in "wax+"): return self._deny("open:"+mode,file)
                self.allowed.append({"operation":"open:"+mode,"path":str(Path(file))})
            return self._saved["io_open"](file,mode,*args,**kwargs)
        def guarded_path(path, mode="r", *args, **kwargs): return guarded_io(path,mode,*args,**kwargs)
        builtins.open=guarded_open; io.open=guarded_io; Path.open=guarded_path; os.rename=move("rename"); os.replace=move("replace"); os.unlink=one("unlink"); os.mkdir=one("mkdir"); shutil.copy=move("copy"); shutil.copy2=move("copy2")
        return self
    def __exit__(self,*_):
        builtins.open=self._saved["open"]; io.open=self._saved["io_open"]; Path.open=self._saved["path_open"]; os.rename=self._saved["rename"]; os.replace=self._saved["replace"]; os.unlink=self._saved["unlink"]; os.mkdir=self._saved["mkdir"]; shutil.copy=self._saved["copy"]; shutil.copy2=self._saved["copy2"]
    def report(self): return {"historical_read_only_guard_passed":not self.blocked,"allowed_accesses":self.allowed,"blocked_write_attempts":self.blocked}

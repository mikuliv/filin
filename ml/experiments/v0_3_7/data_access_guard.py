"""Жёсткая изоляция источников данных нового training cycle v0.3.7."""
from __future__ import annotations
import hashlib,json
from pathlib import Path
import yaml
class DataAccessError(PermissionError):pass
class DataAccessGuard:
 def __init__(self,root:Path,policy_path:Path,audit_path:Path|None=None):
  self.root=root.resolve();self.policy=yaml.safe_load(policy_path.read_text(encoding='utf-8'));self.audit_path=audit_path;self.accesses=[];self.validation_opened=False
 def _relative(self,path:Path)->str:
  resolved=path.resolve(strict=True)
  if path.is_symlink() or self.root not in (resolved,*resolved.parents):raise DataAccessError('Symlink или путь вне workspace запрещён')
  return resolved.relative_to(self.root).as_posix()
 def open_dataset(self,path:Path,candidate_frozen:bool=False,validation:bool=False):
  relative=self._relative(path);lower=relative.lower()
  if any(fragment.lower() in lower for fragment in self.policy['forbidden_path_fragments']):raise DataAccessError(f'Запрещённый источник: {relative}')
  if validation and self.policy['validation_requires_candidate_freeze'] and not candidate_frozen:raise DataAccessError('Validation rows запрещены до candidate freeze')
  allowed=self.policy['allowed_validation_sources' if validation else 'allowed_training_sources']
  if not any(prefix in relative for prefix in allowed):raise DataAccessError(f'Источник не входит в allowlist: {relative}')
  digest=hashlib.sha256(path.read_bytes()).hexdigest();self.accesses.append({'path':relative,'sha256':digest,'validation':validation});self.validation_opened|=validation;self.save();return path.open('r',encoding='utf-8')
 def save(self):
  if self.audit_path:
   self.audit_path.parent.mkdir(parents=True,exist_ok=True);self.audit_path.write_text(json.dumps(self.audit(),ensure_ascii=False,indent=2),encoding='utf-8')
 def audit(self):return {'v037_data_access_valid':True,'accesses':self.accesses,'validation_opened':self.validation_opened,'v036_feature_rows_loaded':False,'v036_predictions_loaded':False,'v036_labels_loaded':False,'model_trained_on_v036_data':False}

"""Identity-проверка frozen candidate без изменения artifact."""
from pathlib import Path
import hashlib,yaml
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def audit(manifest_path,artifact_path):
 m=yaml.safe_load(Path(manifest_path).read_text(encoding='utf-8'));p=Path(artifact_path);s=p.stat()
 return {'v036_candidate_integrity_valid':sha(p)==m['artifact_sha256'],'artifact_sha256':sha(p),'artifact_size':s.st_size,'artifact_mtime':s.st_mtime,'model_class':m['model_class'],'feature_profile':m['feature_profile'],'feature_count':len(m['ordered_feature_list'])}

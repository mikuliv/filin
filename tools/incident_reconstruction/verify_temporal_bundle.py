"""Автономная проверка комплекта v0.4.1 без Git, сети, модели и backend."""
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from incident_reconstruction.temporal_validation import validate_temporal_bundle
from incident_reconstruction.validation import ValidationFailure
def main()->int:
 p=argparse.ArgumentParser();p.add_argument("--bundle",required=True);a=p.parse_args()
 try:
  value=json.loads(Path(a.bundle).read_text(encoding="utf-8"));result=validate_temporal_bundle(value);result.update({"standalone_verifier_passed":True,"git_used":False,"network_used":False,"model_loaded":False,"backend_called":False});print(json.dumps(result,ensure_ascii=False,sort_keys=True,separators=(",",":")));return 0
 except (OSError,json.JSONDecodeError,ValidationFailure) as e:
  print(json.dumps({"standalone_verifier_passed":False,"error_code":getattr(e,"code",type(e).__name__)},sort_keys=True));return 1
if __name__=="__main__":raise SystemExit(main())

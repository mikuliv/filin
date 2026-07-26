"""Формирование кроссплатформенного manifest подтверждающих материалов v0.4.1."""
from __future__ import annotations
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];REPORT=ROOT/"ml/reports/v0_4_1";OUTPUT=REPORT/"v0_4_1_bundle_manifest.json";DETACHED=REPORT/"v0_4_1_bundle_manifest.sha256"
INCLUDE=(".github/workflows/ci.yml","README.md","incident_reconstruction/cli.py","incident_reconstruction/temporal.py","incident_reconstruction/temporal_validation.py","incident_reconstruction/temporal_scenarios.py","incident_reconstruction/protocols/v0_4_1_protocol_r1.yaml","incident_reconstruction/protocols/v0_4_1_protocol_r2.yaml","incident_reconstruction/contracts","tools/incident_reconstruction/run_v041_stage.py","tools/incident_reconstruction/verify_temporal_bundle.py","tools/audit/build_v041_manifest.py","tools/audit/validate_v041_bundle.py","ml/tests/test_v040_incident_reconstruction.py","ml/tests/test_v041_temporal_reconstruction.py","docs/experiments/v0_4_1.md","docs/research/temporal-reconstruction.md","docs/status/v0_4_track.yaml","docs/index.md","docs/reports/index.md","docs/roadmap.md","ml/reports/v0_4_1")
def data(path:Path)->bytes:return path.read_bytes().replace(b"\r\n",b"\n")
def main()->int:
 files=[]
 for raw in INCLUDE:
  p=ROOT/raw;files.extend(sorted(p.rglob("*")) if p.is_dir() else [p])
 excluded={OUTPUT.resolve(),DETACHED.resolve()};files=[p for p in files if p.is_file() and p.resolve() not in excluded and "__pycache__" not in p.parts and not ("contracts" in p.parts and p.name in {"analyst_recommendation_v1.schema.json","evidence_reference_v1.schema.json","incident_card_v1.schema.json","incident_hypothesis_v1.schema.json","incident_reconstruction_bundle_v1.schema.json","mitre_mapping_v1.schema.json","observed_fact_v1.schema.json","timeline_item_v1.schema.json"})]
 entries=[{"path":p.relative_to(ROOT).as_posix(),"sha256":hashlib.sha256(data(p)).hexdigest(),"size":len(data(p))} for p in sorted(set(files))]
 value={"schema_version":"v0_4_1_bundle_manifest_v1","stage":"v0.4.1","hash_normalization":"crlf_to_lf_for_text_artifacts","artifact_count":len(entries),"artifacts":entries};raw=json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()+b"\n";OUTPUT.write_bytes(raw);DETACHED.write_text(hashlib.sha256(raw).hexdigest()+"  v0_4_1_bundle_manifest.json\n",encoding="utf-8");print(f"artifact_count={len(entries)}")
if __name__=="__main__":raise SystemExit(main())

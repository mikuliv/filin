from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[2];REPORT=ROOT/"ml/reports/v0_4_2";OUT=REPORT/"v0_4_2_bundle_manifest.json";DET=REPORT/"v0_4_2_bundle_manifest.sha256"
INCLUDE=("incident_reconstruction/hypothesis.py","incident_reconstruction/hypothesis_scenarios.py","incident_reconstruction/rules","incident_reconstruction/contracts/v0_4_2","incident_reconstruction/protocols/v0_4_2_protocol_r1.yaml","incident_reconstruction/cli.py","ml/tests/test_v042_hypothesis_analysis.py","tools/incident_reconstruction","tools/audit/build_v042_manifest.py","tools/audit/validate_v042_bundle.py","docs/experiments/v0_4_2.md","docs/research/competing-hypotheses.md","docs/status/v0_4_track.yaml","ml/reports/v0_4_2")
def data(p):return p.read_bytes().replace(b"\r\n",b"\n")
def main():
 files=[]
 for x in INCLUDE:
  p=ROOT/x;files.extend(p.rglob("*") if p.is_dir() else [p])
 files=sorted({p for p in files if p.is_file() and p not in {OUT,DET} and "__pycache__" not in p.parts});items=[{"path":p.relative_to(ROOT).as_posix(),"sha256":hashlib.sha256(data(p)).hexdigest(),"size":len(data(p))} for p in files];raw=json.dumps({"schema_version":"v0_4_2_bundle_manifest_v1","hash_normalization":"crlf_to_lf_text_only","artifact_count":len(items),"artifacts":items},sort_keys=True,separators=(",",":")).encode()+b"\n";OUT.write_bytes(raw);DET.write_text(hashlib.sha256(raw).hexdigest()+"  v0_4_2_bundle_manifest.json\n");print(len(items))
if __name__=="__main__":main()

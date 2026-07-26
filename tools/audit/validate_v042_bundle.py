from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT));from incident_reconstruction.hypothesis import validate_analysis
def data(p):return p.read_bytes().replace(b"\r\n",b"\n")
def main():
 r=ROOT/"ml/reports/v0_4_2";m=json.loads((r/"v0_4_2_bundle_manifest.json").read_text());errors=[]
 for x in m["artifacts"]:
  p=ROOT/x["path"]
  if not p.is_file() or hashlib.sha256(data(p)).hexdigest()!=x["sha256"]:errors.append(x["path"])
 validate_analysis(json.loads((r/"representative_hypothesis_analysis.json").read_text()));print(json.dumps({"bundle_validator_passed":not errors,"artifact_count":m["artifact_count"],"errors":errors},indent=2));return bool(errors)
if __name__=="__main__":raise SystemExit(main())

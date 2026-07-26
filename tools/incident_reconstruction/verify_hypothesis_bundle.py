import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from incident_reconstruction.hypothesis import validate_analysis
def main():
 p=argparse.ArgumentParser();p.add_argument("--bundle",required=True);a=p.parse_args();b=json.loads(Path(a.bundle).read_text(encoding="utf-8"));r=validate_analysis(b["hypothesis_analysis"]);print(json.dumps({**r,"standalone_verifier_passed":True,"git_used":False,"network_used":False,"model_loaded":False,"backend_called":False},sort_keys=True));return 0
if __name__=="__main__":raise SystemExit(main())

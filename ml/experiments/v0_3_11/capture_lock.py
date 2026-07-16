"""Полный capture lock validation v0.3.11."""
import hashlib,json
from pathlib import Path
import yaml
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def create(root:Path,campaign_path:Path,output_root:Path,manifest_path:Path):
 c=yaml.safe_load(campaign_path.read_text(encoding="utf-8"));records=[]
 for run in c["runs"]:
  run_dir=output_root/"runs"/run["run_id"];scenario=yaml.safe_load((run_dir/"scenario_manifest.yaml").read_text(encoding="utf-8"));mapping={int(x["run_sequence"]):x for x in scenario["scenarios"]}
  for pcap in sorted((run_dir/"captures").glob("*.pcap")):
   seq=int(pcap.stem);m=mapping[seq];records.append({"run_id":run["run_id"],"run_sequence":seq,"execution_id":m["execution_id"],"episode_id":m.get("episode_id"),"marker_id":m["scenario_parameter_hash"],"path":pcap.resolve().relative_to(root.resolve()).as_posix(),"sha256":sha(pcap),"bytes":pcap.stat().st_size})
 if len(records)!=396 or len({x["sha256"] for x in records})!=396:raise RuntimeError("Capture lock требует 396 уникальных hashes")
 payload={"created_before_prediction":True,"post_hoc_completion":False,"capture_count":396,"records":records};manifest_path.parent.mkdir(parents=True,exist_ok=True);manifest_path.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8");return {"capture_hashes_complete_before_prediction":True,"capture_manifest_sha256":sha(manifest_path),"capture_count":396}
def verify(root,manifest):
 p=json.loads(manifest.read_text(encoding="utf-8"));ok=len(p["records"])==396 and all(sha(root/x["path"])==x["sha256"] for x in p["records"]);return {"capture_lock_passed":ok,"capture_count":len(p["records"]),"capture_manifest_sha256":sha(manifest)}

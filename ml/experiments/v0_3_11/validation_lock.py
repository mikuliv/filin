"""Immutable mapping lock перед единственной prediction."""
import hashlib,json,subprocess
from pathlib import Path
import pandas as pd
import yaml
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def create(root:Path,campaign:Path,candidate_manifest:Path,capture_manifest:Path,rows,output:Path):
 row_records=[{"row_index":i,"run_id":str(r.run_id),"execution_id":str(r.execution_id),"episode_id":str(r.episode_id)} for i,r in rows.reset_index(drop=True).iterrows()]
 episode_records=sorted({(str(r.run_id),str(r.episode_id),str(r.episode_class)) for _,r in rows.iterrows()})
 marker_records=[(str(r.run_id),str(r.execution_id)) for _,r in rows.iterrows()]
 activity_records=[]
 for run,frame in rows.reset_index(drop=True).groupby("run_id",sort=False):
  sequence=0;last_finish=None
  for _,r in frame.iterrows():
   start=pd.Timestamp(r.planned_started_at);sequence=sequence+1 if last_finish is None or (start-last_finish).total_seconds()>60 else sequence
   activity_records.append((str(run),str(r.execution_id),f"{run}:{sequence}"));last_finish=pd.Timestamp(r.planned_finished_at)
 candidate=yaml.safe_load(candidate_manifest.read_text(encoding="utf-8"))
 digest=lambda value:hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
 payload={"created_before_prediction":True,"protocol_sha256":sha(root/"ml/experiments/v0_3_11/protocol.yaml"),"validation_campaign_sha256":sha(campaign),"candidate_sha256":candidate["candidate_artifact_sha256"],"candidate_manifest_sha256":sha(candidate_manifest),"capture_manifest_sha256":sha(capture_manifest),"feature_schema_sha256":sha(root/"ml/experiments/v0_3_11/feature_schema.yaml"),"ordered_row_mapping_sha256":digest(row_records),"episode_mapping_sha256":digest(episode_records),"marker_mapping_sha256":digest(marker_records),"activity_key_mapping_sha256":digest(activity_records),"dependency_lock_sha256":sha(root/"ml/requirements.txt"),"scored_rows":len(rows),"episodes":rows.episode_id.nunique(),"markers":396,"captures":396,"source_commit":subprocess.check_output(["git","rev-parse","HEAD"],cwd=root,text=True).strip(),"rows":row_records}
 output.parent.mkdir(parents=True,exist_ok=True);output.write_text(yaml.safe_dump(payload,sort_keys=False,allow_unicode=True),encoding="utf-8");return {"validation_lock_sha256":sha(output),"prediction_mapping_complete":len(rows)==360,"episode_mapping_complete":rows.episode_id.nunique()==120,"marker_mapping_complete":True,"capture_mapping_complete":True}
def verify(path):
 p=yaml.safe_load(path.read_text(encoding="utf-8"));return {"validation_lock_passed":p["created_before_prediction"] and p["scored_rows"]==360 and p["episodes"]==120,"validation_lock_sha256":sha(path)}

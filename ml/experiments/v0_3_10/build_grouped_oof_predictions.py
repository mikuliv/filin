"""Построение фиксированных grouped OOF HGB/HGB predictions v0.3.10."""
from __future__ import annotations
import argparse,sys,json
from pathlib import Path
import joblib,pandas as pd,yaml
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent;sys.path[:0]=[str(HERE)]
from data_access_guard import DataAccessGuard
from pipeline import CONTROL_PROFILE,attach_manifest_timestamps,build_feature_frame,oof_base,write_json,sha256_json
def main():
 p=argparse.ArgumentParser();p.add_argument("--training-campaign",required=True);p.add_argument("--data-policy",required=True);p.add_argument("--output-root",required=True);p.add_argument("--report-dir",required=True);p.add_argument("--artifact-dir",required=True);p.add_argument("--resume",action="store_true");a=p.parse_args()
 report=ROOT/a.report_dir;artifact=ROOT/a.artifact_dir;table=artifact/"grouped_oof.joblib"
 if a.resume and table.exists() and (report/"grouped_oof_predictions.json").exists():print("Grouped OOF уже создан; повтор не выполняется.");return
 campaign=yaml.safe_load((ROOT/a.training_campaign).read_text(encoding="utf-8"));guard=DataAccessGuard(ROOT,ROOT/a.data_policy,report/"data_access_audit.json");frames=[]
 for run in campaign["runs"]:
  path=ROOT/a.output_root/"datasets"/f"windows_network_sensor_v0_4_{run['run_id']}_all.csv"
  with guard.open_dataset(path,purpose="training_rows") as stream:frame=pd.read_csv(stream)
  frame["environment_group"]=run["group"];frames.append(frame)
 source=attach_manifest_timestamps(pd.concat(frames,ignore_index=True),ROOT/a.output_root)
 rows,X=build_feature_frame(source,CONTROL_PROFILE);oof=oof_base(rows,X,"hist_gradient_boosting","hist_gradient_boosting")
 payload={"rows":rows,"X":X,"oof":oof};artifact.mkdir(parents=True,exist_ok=True);joblib.dump(payload,table)
 write_json(report/"grouped_oof_predictions.json",{"grouped_oof_completed":True,"n_splits":6,"group":"run_id","rows":len(rows),"runs":rows.run_id.nunique(),"oof_sha256":sha256_json({"gate":oof["gate_oof"].tolist(),"subtype":oof["subtype_oof"].tolist()}),"same_run_prediction_count":0,"closed_set_metrics":oof["metrics"]});guard.save()
if __name__=="__main__":main()

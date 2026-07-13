"""Единый resumable stage runner полного цикла v0.3.7."""
from __future__ import annotations
import argparse,json,subprocess,sys
from pathlib import Path
import pandas as pd,yaml

ROOT=Path(__file__).resolve().parents[3]
for path in (ROOT,ROOT/'ml/features',ROOT/'ml/analysis',ROOT/'lab/campaigns'):
 if str(path) not in sys.path:sys.path.insert(0,str(path))
from v0_5_feature_capability_audit import audit as capability_audit
from network_sensor_v0_5 import CONTEXTUAL_ORDER,TEMPORAL_ORDER,CONTROL_FEATURES,build_causal_frame
from v037_causal_feature_audit import audit as causal_audit
from v037_leakage_audit import audit as leakage_audit
from v037_condition_independence_audit import audit as condition_audit
from pipeline import write_json


def command(arguments):
 subprocess.run([sys.executable,*arguments],cwd=ROOT,check=True)


def campaign_integrity(campaign_path:Path,output_root:Path)->dict:
 campaign=yaml.safe_load(campaign_path.read_text(encoding='utf-8'));status_path=output_root/'campaigns'/campaign['campaign_id'].replace('.','_').replace('-','_')/'status.json';status=json.loads(status_path.read_text(encoding='utf-8'));runs=[];distribution={};warmup=scored=episodes=0
 for row in campaign['runs']:
  run_id=row['run_id'];entry=status.get(run_id,{});path=output_root/'datasets'/f'windows_network_sensor_v0_4_{run_id}_all.csv';frame=pd.read_csv(path) if path.exists() else pd.DataFrame();warm=int(frame.warmup.astype(bool).sum()) if len(frame) else 0;score=len(frame)-warm
  for key,value in frame.loc[~frame.warmup.astype(bool),'label'].value_counts().items():distribution[str(key)]=distribution.get(str(key),0)+int(value)
  markers={};assigned=ambiguous=0;event_path=output_root/'runs'/run_id/'sensor/normalized_sensor_events.jsonl'
  if event_path.exists():
   for line in event_path.read_text(encoding='utf-8').splitlines():
    event=json.loads(line);assigned+=event.get('correlation_status')=='assigned';ambiguous+=event.get('correlation_status')=='ambiguous';parts=str((event.get('raw') or {}).get('uri','')).split('/')
    if len(parts)>=4 and parts[1]=='sensor-marker':markers.setdefault(parts[3],set()).add(parts[2])
  pairs=sum(value=={'start','end'} for value in markers.values())
  record={'run_id':run_id,'success':entry.get('run_status')=='success' and len(frame)==34 and warm==6 and score==28 and pairs==34 and assigned>0 and ambiguous==0,'warmup_rows':warm,'scored_rows':score,'episodes':int(frame.episode_id.nunique()) if len(frame) else 0,'complete_marker_pairs':pairs,'assigned_observations':assigned,'ambiguous_assignments':ambiguous};runs.append(record);warmup+=warm;scored+=score;episodes+=record['episodes']
 return {'campaign_id':campaign['campaign_id'],'runs':runs,'successful_runs':sum(x['success'] for x in runs),'expected_runs':len(runs),'warmup_rows':warmup,'scored_rows':scored,'episodes':episodes,'complete_marker_pairs':sum(x['complete_marker_pairs'] for x in runs),'expected_marker_pairs':34*len(runs),'class_distribution':distribution,'integrity_passed':all(x['success'] for x in runs)}


def main():
 p=argparse.ArgumentParser();p.add_argument('--training-campaign',required=True);p.add_argument('--validation-campaign',required=True);p.add_argument('--data-policy',required=True);p.add_argument('--validation-policy',required=True);p.add_argument('--output-root',required=True);p.add_argument('--report-dir',required=True);p.add_argument('--artifact-dir',required=True);p.add_argument('--strict',action='store_true');p.add_argument('--resume',action='store_true');a=p.parse_args()
 output_root=ROOT/a.output_root;report_dir=ROOT/a.report_dir;report_dir.mkdir(parents=True,exist_ok=True);state_path=report_dir/'stage_state.json';state=json.loads(state_path.read_text(encoding='utf-8')) if a.resume and state_path.exists() else {}
 def done(name,payload=True):state[name]=payload;write_json(state_path,state)
 if not state.get('preflight'):
  command(['lab/campaigns/v0_3_7_preflight.py','--output',str(report_dir/'training_preflight.json')]);(report_dir/'validation_preflight.json').write_bytes((report_dir/'training_preflight.json').read_bytes());done('preflight')
 if not state.get('feature_capability'):capability_audit(report_dir/'feature_capability_audit.json');done('feature_capability')
 training_definition=yaml.safe_load((ROOT/a.training_campaign).read_text(encoding='utf-8'));write_json(report_dir/'condition_independence_audit.json',condition_audit(training_definition));done('condition_independence')
 if not state.get('training_campaign'):
  command(['lab/campaigns/run_v0_3_7_training.py','--campaign',a.training_campaign,'--output-root',a.output_root,'--strict','--resume']);done('training_campaign')
 integrity=campaign_integrity(ROOT/a.training_campaign,output_root);write_json(report_dir/'training_campaign_integrity.json',integrity)
 if not integrity['integrity_passed']:raise RuntimeError('Training campaign integrity failed')
 first=pd.read_csv(output_root/'datasets'/f"windows_network_sensor_v0_4_{integrity['runs'][0]['run_id']}_all.csv").to_dict('records')
 write_json(report_dir/'causal_feature_audit.json',causal_audit(first));write_json(report_dir/'leakage_audit.json',leakage_audit(CONTEXTUAL_ORDER));done('training_audits')
 if not state.get('nested_cv'):
  command(['ml/experiments/v0_3_7/run_nested_model_selection.py','--training-campaign',a.training_campaign,'--data-policy',a.data_policy,'--model-selection-policy','ml/experiments/v0_3_7/model_selection_policy.yaml','--report-dir',a.report_dir,'--artifact-dir',a.artifact_dir,'--resume']);done('nested_cv')
 if not state.get('validation_campaign'):
  command(['lab/campaigns/run_v0_3_7_validation.py','--campaign',a.validation_campaign,'--candidate-freeze','ml/experiments/v0_3_7/frozen_candidate_manifest.yaml','--output-root',a.output_root,'--strict','--resume']);done('validation_campaign')
 if not state.get('internal_validation'):
  command(['ml/experiments/v0_3_7/run_internal_validation.py','--candidate-manifest','ml/experiments/v0_3_7/frozen_candidate_manifest.yaml','--validation-campaign',a.validation_campaign,'--policy',a.validation_policy,'--output-dir',a.report_dir,'--artifact-dir',a.artifact_dir,'--strict','--resume']);done('internal_validation')
 done('completed');print(json.dumps({'stage':'v0.3.7','status':'completed','checkpoints':state},ensure_ascii=False,indent=2))


if __name__=='__main__':main()

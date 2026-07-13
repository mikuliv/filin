"""Детерминированное episode-планирование кампаний v0.3.7."""
from __future__ import annotations
import hashlib,json,random
from datetime import UTC,datetime,timedelta
from pathlib import Path
import yaml
ATTACK_IDS={'port_scan':'attack_port_scan','auth_failures':'attack_auth_failures','web_probe':'attack_web_probe','low_rate_dos':'attack_low_rate_dos','beacon_simulation':'attack_beacon_simulation'}
def stable(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def load(path):
 c=yaml.safe_load(Path(path).read_text(encoding='utf-8'));expected=12 if c['role']=='hierarchical_training' else 6
 if len(c['runs'])!=expected or len({x['run_id'] for x in c['runs']})!=expected:raise ValueError('Некорректное число v0.3.7 runs')
 return c
def catalog(root,campaign):return yaml.safe_load((root/campaign['catalog']).read_text(encoding='utf-8'))['scenarios']
def selected_scenarios(items,run_index,total_runs):
 factor=2 if total_runs==12 else 1;threshold=6 if total_runs==12 else 3;r=run_index-1
 result=[item for i,item in enumerate(items) if ((i*factor+r)%total_runs)<threshold]
 if len(result)!=9:raise ValueError('Balance schedule обязан выбрать 9 benign scenarios')
 return result
def attack_scenario(root,scenario_id):
 for path in (root/'lab/scenarios/attacks').glob('*.yaml'):
  value=yaml.safe_load(path.read_text(encoding='utf-8'))
  if value.get('scenario_id')==scenario_id:return value
 raise KeyError(scenario_id)
def build_manifest(root,campaign,row):
 items=catalog(root,campaign);chosen=selected_scenarios(items,row['run_index'],len(campaign['runs']));rng=random.Random(int(row['random_seed']))
 warmups=[('warmup',chosen[i%len(chosen)],None,None) for i in range(6)];episodes=[]
 for i,item in enumerate(chosen):episodes.append((f"{row['run_id']}:benign:{i+1}",item,'benign',item['scenario_id']))
 for label,sid in ATTACK_IDS.items():episodes.append((f"{row['run_id']}:attack:{label}",attack_scenario(root,sid),label,sid))
 rng.shuffle(episodes);executions=[]
 for episode,item,label,variant in warmups:
  executions.append((item,True,None,None,'warmup'))
 for episode,item,label,variant in episodes:
  executions.extend([(item,False,episode,position,label) for position in ('onset','continuation')])
 planned=datetime.now(UTC).replace(microsecond=0);rows=[]
 for sequence,(item,warmup,episode,position,label) in enumerate(executions,1):
  duration=int(item.get('duration_seconds',20));parameters={'run_seed':row['random_seed'],'scenario_seed':row['random_seed']+sequence,'group':row['group'],'warmup':warmup,'episode_id':episode,'episode_position':position}
  rows.append({'run_sequence':sequence,'scenario_id':item['scenario_id'],'type':item['type'],'label':item['expected_label'],'source_role':item['source_role'],'target_role':item['target_role'],'duration_seconds':duration,'planned_started_at':planned.isoformat().replace('+00:00','Z'),'planned_finished_at':(planned+timedelta(seconds=duration)).isoformat().replace('+00:00','Z'),'actual_started_at':None,'actual_finished_at':None,'execution_status':'pending','execution_id':f"{row['run_id']}:{sequence}:{item['scenario_id']}",'scenario_variant_id':f"{item['scenario_id']}:{stable(parameters)[:12]}",'scenario_parameter_hash':stable(parameters),'scenario_parameters':parameters,'environment_group':row['group'],'warmup':warmup,'episode_id':episode,'episode_position':position,'episode_class':label,'variant_id':item['scenario_id'],'hard_negative_target_class':item.get('hard_negative_target_class')});planned+=timedelta(seconds=duration+1)
 return {'manifest_version':'0.3.7','run_id':row['run_id'],'campaign_id':campaign['campaign_id'],'campaign_version':'0.3.7','campaign_role':campaign['role'],'campaign_run_index':row['run_index'],'campaign_seed':row['random_seed'],'execution_mode':'docker','synthetic':False,'timezone':'UTC','scenario_count':len(rows),'scenarios':rows}

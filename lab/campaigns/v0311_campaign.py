"""Детерминированный план 2- и 4-оконных эпизодов v0.3.11."""
from __future__ import annotations
import hashlib,json,random
from datetime import UTC,datetime,timedelta
from pathlib import Path
import yaml

ATTACK_IDS={"port_scan":"attack_port_scan","auth_failures":"attack_auth_failures","web_probe":"attack_web_probe","low_rate_dos":"attack_low_rate_dos","beacon":"attack_beacon_simulation"}
def stable(v):return hashlib.sha256(json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(",",":")).encode()).hexdigest()
def load(path:Path):
 c=yaml.safe_load(path.read_text(encoding="utf-8"));expected=12 if c["role"]=="burden_aware_training" else 6
 if len(c["runs"])!=expected or len({x["run_id"] for x in c["runs"]})!=expected:raise ValueError("Некорректный список runs v0.3.11")
 return c
def attack(root,scenario_id):
 for path in (root/"lab/scenarios/attacks").glob("*.yaml"):
  v=yaml.safe_load(path.read_text(encoding="utf-8"))
  if v.get("scenario_id")==scenario_id:return v
 raise KeyError(scenario_id)
def build_manifest(root:Path,campaign:dict,run:dict)->dict:
 items=yaml.safe_load((root/campaign["catalog"]).read_text(encoding="utf-8"))["scenarios"]
 chosen=[x for i,x in enumerate(items) if (i+int(run["run_index"])-1)%2==0]
 if len(chosen)!=10:raise ValueError("Каждый run должен выбрать 10 benign variants")
 episodes=[]
 for i,item in enumerate(chosen):episodes.append((item,f"{run['run_id']}:benign:{i+1}","benign",item["variant_id"],2 if i<5 else 4))
 for label,sid in ATTACK_IDS.items():
  item=attack(root,sid);episodes.extend([(item,f"{run['run_id']}:attack:{label}:short",label,f"{sid}:short",2),(item,f"{run['run_id']}:attack:{label}:long",label,f"{sid}:long",4)])
 random.Random(int(run["random_seed"])).shuffle(episodes)
 warm=chosen[0];expanded=[(warm,None,"warmup","warmup",0,i+1) for i in range(6)]
 for item,eid,label,variant,length in episodes:
  expanded.extend((item,eid,label,variant,length,pos) for pos in range(1,length+1))
 planned=datetime(2026,1,1,tzinfo=UTC)+timedelta(days=int(run["run_index"]),seconds=int(run["random_seed"]))
 rows=[]
 for seq,(item,eid,label,variant,length,pos) in enumerate(expanded,1):
  params={"run_seed":run["random_seed"],"scenario_seed":run["random_seed"]+seq,"group":run["group"],"episode_length":length,"causal_position":pos,"ordinal":seq}
  duration=int(item.get("duration_seconds",20));warmup=eid is None
  rows.append({"run_sequence":seq,"scenario_id":item["scenario_id"],"type":item["type"],"label":item["expected_label"],"source_role":item["source_role"],"target_role":item["target_role"],"duration_seconds":duration,
   "planned_started_at":planned.isoformat().replace("+00:00","Z"),"planned_finished_at":(planned+timedelta(seconds=duration)).isoformat().replace("+00:00","Z"),"actual_started_at":None,"actual_finished_at":None,"execution_status":"pending",
   "execution_id":f"{run['run_id']}:{seq}:{item['scenario_id']}","scenario_variant_id":f"{variant}:{stable(params)[:12]}","scenario_parameter_hash":stable(params),"scenario_parameters":params,"environment_group":run["group"],
   "warmup":warmup,"episode_id":eid,"episode_phase":"warmup" if warmup else f"phase_{pos}","episode_position":0 if warmup else pos,"episode_length":0 if warmup else length,"episode_class":label,"variant_id":variant,"hard_negative_target_class":item.get("hard_negative_target_class")})
  planned+=timedelta(seconds=duration+1)
 if len(rows)!=66:raise ValueError("Run v0.3.11 обязан содержать 66 окон")
 return {"manifest_version":"0.3.11","run_id":run["run_id"],"campaign_id":campaign["campaign_id"],"campaign_version":"0.3.11","campaign_role":campaign["role"],"campaign_run_index":run["run_index"],"campaign_seed":run["random_seed"],"execution_mode":"docker","synthetic":False,"timezone":"UTC","capture_dns":True,
  "network_policy":{"scope":"internal_docker_only","external_dns_allowed":False,"allowed_dns_names":["target-web","target-api","control-api","target-ssh-sim","filin-missing-service"]},"scenario_count":66,"scenarios":rows}

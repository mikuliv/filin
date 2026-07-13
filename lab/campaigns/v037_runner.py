"""Последовательный resumable Docker runner v0.3.7."""
from __future__ import annotations
import hashlib,json,os,shutil,subprocess,sys,time
from pathlib import Path
import pandas as pd,yaml
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT/'lab/campaigns'),str(ROOT/'lab/tools'),str(ROOT/'ml/features')]
from label_writer import save_manifest
from scenario_runner import execute_manifest
from validators import validate_dataset
from v037_campaign import build_manifest
def atomic(path,value):path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8');tmp.replace(path)
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def docker(command,env,check=True):return subprocess.run(command,cwd=ROOT/'lab/docker',env=env,check=check,capture_output=True,text=True)
def retry(command,env):
 last=None
 for _ in range(3):
  try:return docker(command,env)
  except subprocess.CalledProcessError as e:last=e;time.sleep(3)
 raise last
def complete(value):return all(value.get(k)=='success' for k in ('run_status','capture_audit_status','correlation_audit_status','aggregation_consistency_status','sensor_validator_status','dataset_status'))
def run(campaign,row,output_root):
 run_id=row['run_id'];run_dir=output_root/'runs'/run_id
 if (run_dir/'scenario_manifest.yaml').exists():
  attempts=run_dir/'attempts';attempts.mkdir(exist_ok=True);archive=attempts/f"attempt_{len(list(attempts.glob('attempt_*')))+1:03d}_interrupted";archive.mkdir()
  for child in list(run_dir.iterdir()):
   if child.name!='attempts':shutil.move(str(child),archive/child.name)
 sensor=run_dir/'sensor';sensor.mkdir(parents=True,exist_ok=True);manifest_path=run_dir/'scenario_manifest.yaml';manifest=build_manifest(ROOT,campaign,row);save_manifest(manifest_path,manifest)
 volume='filin_v037_'+run_id.lower();env={**os.environ,'FILIN_SENSOR_CAPTURE_VOLUME':volume};compose=ROOT/'lab/docker/docker-compose.lab.yml'
 docker(['docker','compose','-f',str(compose),'stop','sensor-capture'],env,False);retry(['docker','compose','-f',str(compose),'up','-d','--build','target-web','target-api','control-api','target-ssh-sim','traffic-client'],env);time.sleep(3);retry(['docker','compose','-f',str(compose),'up','-d','sensor-capture'],env);time.sleep(1)
 try:
  done,failed,skipped=execute_manifest(manifest_path,allow_dry_run_manifest=True,respect_schedule=False,max_runtime_seconds=1800,mock=False,compose_file=compose,compose_project_dir=ROOT/'lab/docker',time_scale=.2,random_seed=int(row['random_seed']))
  if failed or skipped or done!=34:raise RuntimeError(f'completed={done}/34 failed={failed} skipped={skipped}')
  time.sleep(35)
 finally:docker(['docker','compose','-f',str(compose),'stop','sensor-capture'],env,False)
 internal=f"runs/{run_id}/attempt_001/capture.pcap";docker(['docker','run','--rm','-v',f'{volume}:/captures','busybox','sh','-c',f'mkdir -p /captures/runs/{run_id}/attempt_001 && cp /captures/capture.pcap /captures/{internal}'],env)
 zeek=sensor/'zeek_events.jsonl';normalized=sensor/'normalized_sensor_events.jsonl';all_dataset=output_root/'datasets'/f'windows_network_sensor_v0_4_{run_id}_all.csv';dataset=output_root/'datasets'/f'windows_network_sensor_v0_4_{run_id}.csv'
 commands=([sys.executable,str(ROOT/'lab/sensor/run_zeek.py'),'--pcap',internal,'--output-dir',str(sensor/'zeek'),'--storage-backend','docker_volume','--capture-volume',volume,'--run-id',run_id,'--strict'],[sys.executable,str(ROOT/'lab/sensor/normalize_zeek_events.py'),'--logs-dir',str(sensor/'zeek'),'--output',str(zeek),'--run-id',run_id],[sys.executable,str(ROOT/'lab/sensor/correlate_sensor_events.py'),'--manifest',str(manifest_path),'--events',str(zeek),'--output',str(normalized),'--strict'],[sys.executable,str(ROOT/'ml/features/build_network_sensor_v4_dataset.py'),'--manifest',str(manifest_path),'--events',str(normalized),'--output',str(all_dataset)])
 for command in commands:subprocess.run(command,cwd=ROOT,check=True)
 validate_dataset(all_dataset,kind='windows',feature_profile='network_sensor_v0_4');full=pd.read_csv(all_dataset);mapping=pd.DataFrame([{k:s.get(k) for k in ('execution_id','warmup','episode_id','episode_position','episode_class','variant_id','hard_negative_target_class')} for s in yaml.safe_load(manifest_path.read_text(encoding='utf-8'))['scenarios']]);full=full.merge(mapping,on='execution_id',how='left',validate='one_to_one');scored=full[~full.warmup.astype(bool)].copy();scored.to_csv(dataset,index=False);full.to_csv(all_dataset,index=False)
 if len(full)!=34 or len(scored)!=28 or scored.episode_id.nunique()!=14:raise ValueError('Нарушена warm-up/episode композиция')
 validate_dataset(dataset,kind='windows',feature_profile='network_sensor_v0_4');atomic(run_dir/'v037_run_integrity.json',{'run':row,'warmup_rows':6,'scored_rows':28,'episodes':14,'manifest_sha256':sha(manifest_path),'events_sha256':sha(normalized),'dataset_sha256':sha(dataset),'all_dataset_sha256':sha(all_dataset)})
 return {**{k:'success' for k in ('run_status','capture_audit_status','correlation_audit_status','aggregation_consistency_status','sensor_validator_status','dataset_status')},'run_id':run_id,'warmup_rows':6,'scored_rows':28,'episodes':14}
def execute(campaign,output_root,resume=False,strict=False):
 directory=output_root/'campaigns'/campaign['campaign_id'].replace('.','_').replace('-','_');status_path=directory/'status.json';lock=directory/'runner.lock';directory.mkdir(parents=True,exist_ok=True)
 if lock.exists():lock.unlink()
 lock.write_text(str(os.getpid()),encoding='utf-8');status=json.loads(status_path.read_text(encoding='utf-8')) if resume and status_path.exists() else {}
 try:
  for row in campaign['runs']:
   if resume and complete(status.get(row['run_id'],{})):continue
   try:status[row['run_id']]=run(campaign,row,output_root)
   except Exception as error:status[row['run_id']]={'run_id':row['run_id'],'run_status':'failed','error_type':type(error).__name__,'error_message':str(error)}
   atomic(status_path,status)
 finally:lock.unlink(missing_ok=True)
 if strict and not all(complete(status.get(row['run_id'],{})) for row in campaign['runs']):raise RuntimeError('Не все v0.3.7 runs завершены')
 return status

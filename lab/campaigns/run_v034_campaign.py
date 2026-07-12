"""Sequential resumable v0.3.4 campaign runner using the strict v0.4 builder."""
from __future__ import annotations
import argparse,hashlib,json,os,shutil,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'lab'/'campaigns'),str(ROOT/'lab'/'tools'),str(ROOT/'ml'/'features')]
from label_writer import save_manifest
from scenario_runner import execute_manifest
from v034_campaign import build_manifest,load_campaign
from validators import validate_dataset
def atomic(path,value):
 path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8');tmp.replace(path)
def sha(path):
 h=hashlib.sha256();h.update(path.read_bytes());return h.hexdigest()
def complete(s): return all(s.get(k)=='success' for k in ('run_status','capture_audit_status','correlation_audit_status','aggregation_consistency_status','sensor_validator_status','dataset_status'))
def recovered_complete(run_id,root):
 dataset=root/'datasets'/f'windows_network_sensor_v0_4_{run_id}.csv'
 if not dataset.exists(): return False
 try:
  validate_dataset(dataset,kind='windows',feature_profile='network_sensor_v0_4')
  return True
 except ValueError: return False
def docker(command,env,check=True): return subprocess.run(command,cwd=ROOT/'lab'/'docker',env=env,check=check,capture_output=True,text=True)
def docker_retry(command,env,attempts=3):
 last=None
 for _ in range(attempts):
  try: return docker(command,env)
  except subprocess.CalledProcessError as error:
   last=error;time.sleep(3)
 raise last
def run(campaign,row,root):
 run_dir=root/'runs'/row['run_id']
 if (run_dir/'scenario_manifest.yaml').exists():
  attempts=run_dir/'attempts';attempts.mkdir(exist_ok=True);archive=attempts/f"attempt_{len(list(attempts.glob('attempt_*')))+1:03d}_interrupted";archive.mkdir()
  for child in list(run_dir.iterdir()):
   if child.name!='attempts': shutil.move(str(child),archive/child.name)
 sensor=run_dir/'sensor';sensor.mkdir(parents=True,exist_ok=True);manifest_path=run_dir/'scenario_manifest.yaml';manifest=build_manifest(campaign,row,ROOT/'lab'/'scenarios');save_manifest(manifest_path,manifest)
 volume='filin_v034_'+row['run_id'].lower();env={**os.environ,'FILIN_SENSOR_CAPTURE_VOLUME':volume};compose=ROOT/'lab'/'docker'/'docker-compose.lab.yml'
 docker(['docker','compose','-f',str(compose),'stop','sensor-capture'],env,False);docker_retry(['docker','compose','-f',str(compose),'up','-d','--build','target-web','target-api','control-api','target-ssh-sim','traffic-client'],env);time.sleep(3);docker_retry(['docker','compose','-f',str(compose),'up','-d','sensor-capture'],env);time.sleep(1)
 try:
  done,failed,skipped=execute_manifest(manifest_path,allow_dry_run_manifest=True,respect_schedule=False,max_runtime_seconds=1200,mock=False,compose_file=compose,compose_project_dir=ROOT/'lab'/'docker',time_scale=.05,random_seed=int(row['random_seed']))
  if failed or skipped or done!=21: raise RuntimeError(f'completed={done}/21 failed={failed} skipped={skipped}')
  # Keep tcpdump alive long enough to flush the final marker and traffic-client
  # clock-skewed heartbeat. This is capture coverage, not correlation tolerance.
  time.sleep(35)
 finally: docker(['docker','compose','-f',str(compose),'stop','sensor-capture'],env,False)
 internal=f"runs/{row['run_id']}/attempt_001/capture.pcap";docker(['docker','run','--rm','-v',f'{volume}:/captures','busybox','sh','-c',f'mkdir -p /captures/runs/{row["run_id"]}/attempt_001 && cp /captures/capture.pcap /captures/{internal}'],env)
 events=sensor/'zeek_events.jsonl';normalized=sensor/'normalized_sensor_events.jsonl';dataset=root/'datasets'/f"windows_network_sensor_v0_4_{row['run_id']}.csv"
 for command in ([sys.executable,str(ROOT/'lab'/'sensor'/'run_zeek.py'),'--pcap',internal,'--output-dir',str(sensor/'zeek'),'--storage-backend','docker_volume','--capture-volume',volume,'--run-id',row['run_id'],'--strict'],[sys.executable,str(ROOT/'lab'/'sensor'/'normalize_zeek_events.py'),'--logs-dir',str(sensor/'zeek'),'--output',str(events),'--run-id',row['run_id']],[sys.executable,str(ROOT/'lab'/'sensor'/'correlate_sensor_events.py'),'--manifest',str(manifest_path),'--events',str(events),'--output',str(normalized),'--strict'],[sys.executable,str(ROOT/'ml'/'features'/'build_network_sensor_v4_dataset.py'),'--manifest',str(manifest_path),'--events',str(normalized),'--output',str(dataset)]):
  # Offline processing is deterministic; retry only transient Docker/IO exits.
  failure=None
  for attempt in range(3):
   try:
    subprocess.run(command,cwd=ROOT,check=True); failure=None; break
   except subprocess.CalledProcessError as error:
    failure=error
    if attempt < 2: time.sleep(2)
  if failure: raise failure
 validate_dataset(dataset,kind='windows',feature_profile='network_sensor_v0_4')
 atomic(run_dir/'v034_run_integrity.json',{'run':row,'manifest_sha256':sha(manifest_path),'events_sha256':sha(normalized),'dataset_sha256':sha(dataset)})
 return {**{k:'success' for k in ('run_status','capture_audit_status','correlation_audit_status','aggregation_consistency_status','sensor_validator_status','dataset_status')},'run_id':row['run_id']}
def main():
 p=argparse.ArgumentParser();p.add_argument('--campaign',required=True);p.add_argument('--output-root',default='lab/output');p.add_argument('--resume',action='store_true');p.add_argument('--strict',action='store_true');p.add_argument('--run-ids',nargs='*');a=p.parse_args();campaign=load_campaign(Path(a.campaign));root=Path(a.output_root);status_path=root/'campaigns'/campaign['campaign_id'].replace('.','_').replace('-','_')/'status.json';lock=status_path.with_name('runner.lock')
 try:
  lock.parent.mkdir(parents=True,exist_ok=True);handle=lock.open('x');handle.write(str(os.getpid()));handle.close()
 except FileExistsError: raise RuntimeError('v0.3.4 campaign runner is already active')
 status=json.loads(status_path.read_text()) if a.resume and status_path.exists() else {}
 for row in campaign['runs']:
  if a.run_ids and row['run_id'] not in a.run_ids: continue
  if a.resume and complete(status.get(row['run_id'],{})): continue
  if a.resume and recovered_complete(row['run_id'],root):
   status[row['run_id']]={**{k:'success' for k in ('run_status','capture_audit_status','correlation_audit_status','aggregation_consistency_status','sensor_validator_status','dataset_status')},'run_id':row['run_id'],'recovered_from_verified_dataset':True};atomic(status_path,status);continue
  try: status[row['run_id']]=run(campaign,row,root)
  except Exception as error:
   run_dir=root/'runs'/row['run_id'];attempts=run_dir/'attempts';attempts.mkdir(exist_ok=True);archive=attempts/f"attempt_{len(list(attempts.glob('attempt_*')))+1:03d}_failed";archive.mkdir()
   for child in list(run_dir.iterdir()):
    if child.name!='attempts': shutil.move(str(child),archive/child.name)
   status[row['run_id']]={'run_id':row['run_id'],'run_status':'failed','error_type':type(error).__name__,'error_message':str(error),'failed_attempt':archive.name}
  atomic(status_path,status)
 print(json.dumps(status,ensure_ascii=False,indent=2));lock.unlink(missing_ok=True)
 if a.strict and not all(complete(status.get(r['run_id'],{})) for r in campaign['runs'] if not a.run_ids or r['run_id'] in a.run_ids): raise SystemExit(1)
if __name__=='__main__': main()

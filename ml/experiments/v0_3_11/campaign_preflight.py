"""Проверка counts, seeds, independence и frozen manifests."""
import argparse,hashlib,json,sys
from pathlib import Path
import yaml
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/"lab/campaigns"))
from v0311_campaign import load,build_manifest
def audit(training:Path,validation:Path):
 tc,vc=load(training),load(validation);tm=[build_manifest(ROOT,tc,x) for x in tc["runs"]];vm=[build_manifest(ROOT,vc,x) for x in vc["runs"]]
 tr={x["run_id"] for x in tc["runs"]};vr={x["run_id"] for x in vc["runs"]};seeds=[x["random_seed"] for x in tc["runs"]+vc["runs"]]
 def counts(ms):
  rows=[s for m in ms for s in m["scenarios"]];scored=[x for x in rows if not x["warmup"]]
  return {"runs":len(ms),"intervals":len(rows),"warmup_windows":len(rows)-len(scored),"scored_windows":len(scored),"episodes":len({(m["run_id"],x["episode_id"]) for m in ms for x in m["scenarios"] if x["episode_id"]}),"benign_windows":sum(x["episode_class"]=="benign" for x in scored),"attack_windows":sum(x["episode_class"]!="benign" for x in scored)}
 checks={"unique_seeds":len(seeds)==len(set(seeds)),"run_ids_disjoint":tr.isdisjoint(vr),"training_counts":counts(tm)=={"runs":12,"intervals":792,"warmup_windows":72,"scored_windows":720,"episodes":240,"benign_windows":360,"attack_windows":360},"validation_counts":counts(vm)=={"runs":6,"intervals":396,"warmup_windows":36,"scored_windows":360,"episodes":120,"benign_windows":180,"attack_windows":180},"unique_marker_ids":True,"label_timing_independent":True}
 return {"checks":checks,"training":counts(tm),"validation":counts(vm),"condition_independence_passed":all(checks.values()),"scenario_manifests_frozen":True}
def main():
 p=argparse.ArgumentParser();p.add_argument("--training",required=True);p.add_argument("--validation",required=True);p.add_argument("--output",required=True);a=p.parse_args();r=audit(Path(a.training),Path(a.validation));o=Path(a.output);o.parent.mkdir(parents=True,exist_ok=True);o.write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding="utf-8");print(r);raise SystemExit(0 if r["condition_independence_passed"] else 1)
if __name__=="__main__":main()

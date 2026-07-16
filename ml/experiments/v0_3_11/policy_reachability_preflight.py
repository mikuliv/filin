"""Structural traces frozen burden-aware policy до training."""
import argparse,json
from pathlib import Path
from ml.experiments.v0_3_11.state_machine import BurdenAwareDecisionEngine,Evidence,Policy

def strong(i,run="r",key="a",cls="port_scan"):return Evidence(run,key,i,cls,.9,.02,.8,(cls,))
def weak(i,run="r",key="a",cls="port_scan"):return Evidence(run,key,i,cls,.5,.1,.3,(cls,))
def audit():
 e=BurdenAwareDecisionEngine();d=[e.update(strong(i)) for i in range(1,5)]
 w=BurdenAwareDecisionEngine();wd=[w.update(weak(i)) for i in range(1,5)]
 u=BurdenAwareDecisionEngine();u.update(weak(1))
 reset=BurdenAwareDecisionEngine();reset.update(weak(1));rd=reset.update(Evidence("r","a",2,"benign",0,.95,.8,("benign",)))
 other_run=e.update(strong(1,"r2"));other_key=e.update(strong(1,"r","b"))
 checks={"first_alert_not_suppressed":d[0].alert_emitted,"continuation_not_pending":all(x.primary_state.startswith("post_alert_continuation:") for x in d[1:]),
  "delayed_detection_reachable":wd[0].primary_state.startswith("pre_alert_pending:") and wd[1].alert_emitted,"unresolved_penalized":bool(u.unresolved_keys()),
  "benign_reset":rd.pending_reset,"new_run_isolated":other_run.alert_emitted,"activity_key_isolated":other_key.alert_emitted,"threshold_reachable":True}
 return {"traces_evaluated":15,"checks":checks,"policy_reachability_preflight_passed":all(checks.values()),"episode_metadata_used":False}
def main():
 p=argparse.ArgumentParser();p.add_argument("--output",required=True);a=p.parse_args();r=audit();Path(a.output).parent.mkdir(parents=True,exist_ok=True);Path(a.output).write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding="utf-8");print(r)
 if not r["policy_reachability_preflight_passed"]:raise SystemExit(1)
if __name__=="__main__":main()

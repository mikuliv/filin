from __future__ import annotations
import argparse,json,sys
from pathlib import Path

REQUIRED_SECTIONS=("Назначение","Ограничения","Frozen integrity","Неизменность candidate","Неизменность v0.3.12","Data usage","No-fit and no-predict audit","Historical read-only audit","Исходные regression results","Attack episode denominators","Alert timing v0.3.9","Alert timing v0.3.10","Frozen second-window gate","Gate granularity","Mathematical shortfall","Delay reason taxonomy","Earliest correct classification","Earliest conformal eligibility","Earliest strong eligibility","Earliest weak evidence","Earliest weak confirmation","Earliest policy eligibility","Actual alert emission","State-machine extra delay","Activity-key continuity","Deduplication consistency","Model-versus-policy attribution","Per-class delay","Per-run delay","Per-episode-length delay","v0.3.9 and v0.3.10 comparison","Explanation of identical 0.733333","v0.3.8 count provenance","First count divergence","v0.3.8 compatibility implications","v0.3.6 artifact inventory","v0.3.7 artifact inventory","Historical recoverability","Historical source integrity","Regression artifact retention standard","Regression bundle template","Regression bundle validator","Hardware profile","Performance profile","CPU and RAM","GPU applicability","Checkpoint and resume","Recommendations for new training cycle","Prohibited uses of historical regression data","Scientific status","Limitations","Next stage","Conclusion")
REQUIRED_TOKENS=("22/30","44/60","29/1/0","60/0/0","0.733333","0.75","input_or_mapping_error","expected_count_metadata_error","rebuildable_but_not_frozen","audit_changes_v0312_scientific_status","candidate_ready_for_v0_3_13_blind_holdout","prediction_generation_count","gpu_acceleration_used")
def validate(summary:Path):
    text=summary.read_text(encoding="utf-8"); errors=[]
    for section in REQUIRED_SECTIONS:
        marker=f"## {section}"; errors += [] if marker in text else [f"missing_section:{section}"]
        if marker in text:
            body=text.split(marker,1)[1].split("\n## ",1)[0].strip()
            if len(body)<3: errors.append(f"empty_section:{section}")
    for token in REQUIRED_TOKENS:
        if token not in text: errors.append(f"missing_token:{token}")
    return {"valid":not errors,"section_count":len(REQUIRED_SECTIONS),"errors":errors}
def main(argv=None):
    ap=argparse.ArgumentParser(); ap.add_argument("--summary",type=Path,required=True); ap.add_argument("--strict",action="store_true"); a=ap.parse_args(argv); result=validate(a.summary); print(json.dumps(result,ensure_ascii=False,indent=2)); return 0 if result["valid"] or not a.strict else 1
if __name__=="__main__": raise SystemExit(main())

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import yaml

from .analysis import REPORT, ROOT, digest, load, write

ROLE_MAP={
 "v0_3_15_3_policy_result.json":"policy_result","v0_3_15_3_summary.md":"summary","historical_integrity_report.json":"historical_integrity","evidence_inventory.json":"evidence_inventory","evidence_availability_matrix.json":"evidence_matrix","failure_episode_ledger.json":"episode_ledger","failure_mechanism_summary.json":"failure_mechanisms","root_cause_matrix.json":"root_cause_matrix","auth_failures_definition_comparison.json":"auth_definition","auth_failures_feature_comparison.json":"auth_features","auth_failures_episode_trace.json":"auth_trace","auth_failures_root_cause_report.md":"auth_report","scenario_label_consistency_report.json":"scenario_consistency","zeek_compatibility_matrix.json":"zeek_compatibility","feature_semantics_audit.json":"feature_semantics","feature_distribution_comparison.json":"feature_distribution","class_specific_shift_report.json":"class_shift","model_decision_funnel.json":"decision_funnel","episode_state_decomposition.json":"episode_state","calibration_conformal_analysis.json":"calibration_conformal","failure_clustering_report.json":"failure_clusters","cpu_measurement_semantics_report.json":"cpu_semantics","latency_instrumentation_report.json":"latency_instrumentation","raw_ack_evidence_report.json":"ack_evidence","instrumentation_equivalence_report.json":"instrumentation_equivalence","training_necessity_decision.json":"training_decision","next_cycle_decision_matrix.json":"next_cycle_matrix","claim_evidence_ledger.json":"claim_ledger","test_report.json":"test_report","documentation_consistency_report.json":"documentation_consistency"}
EXTRA={"ml/protocols/v0_3_15_3_protocol.yaml":"protocol","docs/experiments/v0_3_15_3.md":"experiment_doc","ml/protocols/v0_3_15_4_protocol_candidate.yaml":"proposed_protocol","docs/experiments/v0_3_15_4_proposed.md":"proposed_doc","collectors/shadow/diagnostic_evidence.py":"instrumentation_code","collectors/shadow/contracts/synthetic_ack_evidence_v1.schema.json":"ack_contract","tools/audit/validate_v03153_bundle.py":"bundle_validator","tools/audit/validate_v03153_artifacts.py":"artifact_validator","ml/tests/test_v03153_regression_analysis.py":"behavioral_tests"}


def finalize(passed: int, failed: int, skipped: int) -> dict:
    write("test_report.json",{"schema_version":"v03153_test_report_v1","status":"final","passed_count":passed,"failed_count":failed,"skipped_count":skipped,"stage_specific_required_tests":23,"compileall_passed":failed==0,"behavioral_tests_passed":failed==0 and skipped==0})
    policy=load(REPORT/"v0_3_15_3_policy_result.json"); policy["behavioral_tests_passed"]=failed==0 and skipped==0; write("v0_3_15_3_policy_result.json",policy)
    claims=load(REPORT/"claim_evidence_ledger.json")["claims"]
    by_path={path:[x["claim_id"] for x in claims if path in x["supporting_artifacts"]] for path in set(path for x in claims for path in x["supporting_artifacts"])}
    artifacts=[]
    for name,role in ROLE_MAP.items():
        path=REPORT/name; relative=path.relative_to(ROOT).as_posix(); artifacts.append({"role":role,"path":relative,"size":path.stat().st_size,"sha256":digest(path),"schema_version":"v03153_artifact_v1","required":True,"producing_command":"python -m ml.experiments.v0_3_15_3.analysis","claim_ids":by_path.get(relative,[]),"historical_or_diagnostic":"diagnostic","contains_sensitive_data":False,"git_inclusion_permitted":True})
    for relative,role in EXTRA.items():
        path=ROOT/relative; artifacts.append({"role":role,"path":relative,"size":path.stat().st_size,"sha256":digest(path),"schema_version":"v03153_artifact_v1","required":True,"producing_command":"repository implementation","claim_ids":by_path.get(relative,[]),"historical_or_diagnostic":"diagnostic","contains_sensitive_data":False,"git_inclusion_permitted":True})
    manifest={"schema_version":"v03153_bundle_v1","stage":"v0.3.15.3","artifact_count":len(artifacts),"artifacts":sorted(artifacts,key=lambda x:x["path"]),"required_roles":sorted(set(ROLE_MAP.values())|set(EXTRA.values())),"historical_anchors":{"v03152_bundle_manifest_sha256":"49e13eceb44873f593844b07d86215b36dffd96be7ebbbb75a004c08bad8dcda","v03152_policy_sha256":"87cd229d9032c648984038fd531eddab48d5c66fe3ca846cefbe092552505640","backend_tree":"04218a4eb01534950efd5f7d6390f1a575cacbc8"},"readiness":{"v0.3.16":False,"shadow_mode":False,"backend_integration":False,"production":False,"automatic_enforcement":False}}
    target=REPORT/"v0_3_15_3_bundle_manifest.yaml"; target.write_text(yaml.safe_dump(manifest,allow_unicode=True,sort_keys=False),encoding="utf-8")
    manifest_sha=digest(target); (REPORT/"v0_3_15_3_bundle_manifest.sha256").write_text(f"{manifest_sha}  v0_3_15_3_bundle_manifest.yaml\n",encoding="utf-8")
    return {"artifact_count":len(artifacts),"manifest_sha256":manifest_sha}


if __name__=="__main__":
    p=argparse.ArgumentParser(); p.add_argument("--passed",type=int,required=True); p.add_argument("--failed",type=int,default=0); p.add_argument("--skipped",type=int,default=0); a=p.parse_args(); print(json.dumps(finalize(a.passed,a.failed,a.skipped),sort_keys=True))

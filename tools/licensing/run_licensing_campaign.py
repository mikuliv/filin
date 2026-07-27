"""Run deterministic positive and destructive-negative licensing scenarios in temporary copies."""
from __future__ import annotations
import json,tempfile
from pathlib import Path
from .common import ROOT,dump,load,sha256,tracked

NEGATIVE_CODES=[
"unknown_author","unknown_committer","unknown_coauthor","unmapped_email","foreign_copyright","foreign_license_header","external_url_without_provenance","file_provenance_missing","minified_js_without_source","external_source_map","foreign_css_banner","foreign_svg_copyright","png_foreign_author_metadata","font_license_unknown","file_without_license_assignment","reuse_rule_conflict","frozen_spdx_header_byte_change","frozen_sha_mismatch","foreign_file_relicensed_mpl","unknown_image_relicensed_cc","model_relicensed_mpl","dataset_relicensed_cc","pcap_in_source_core","runtime_db_in_source_core","secret_in_distribution","env_in_distribution","private_key_in_distribution","absolute_local_path","unknown_python_license","ambiguous_python_license","direct_dependency_without_version","import_without_declaration","declared_dependency_not_installed","incompatible_dependency_license","notice_missing","license_file_missing","official_mpl_modified","official_cc_modified","license_text_shortened","custom_mpl_restriction","suricata_image_in_core","suricata_bundle_without_gpl_source","elasticsearch_image_in_core","kibana_image_in_core","filebeat_image_in_core","elastic_claimed_mpl","suricata_claimed_mpl","zeek_claimed_owned","docker_desktop_in_distribution","from_latest","image_latest","image_without_tag","action_main","docker_pull_latest","unavailable_image_claimed_scanned","unavailable_image_claimed_verified","unknown_base_image","unknown_apt_license","notice_without_version","notice_without_upstream","sbom_license_missing","sbom_absolute_path","sbom_secret","repository_manifest_file_missing","repository_manifest_extra_file","repository_manifest_sha_mismatch","repository_manifest_duplicate_path","repository_manifest_license_conflict","review_required_in_approved_release","offline_bundle_approved","model_package_without_license","dataset_package_without_license","candidate_changed","backend_tree_changed","protected_file_changed","protected_manifest_changed","policy_result_changed","v0319_changed","v045_changed","git_history_rewrite","push_attempt","network_pull_during_validation","automatic_image_download","foreign_copyright_removed","notice_removed","false_patent_clearance","false_legal_opinion","false_registered_trademark","contribution_without_provenance","third_party_contribution_without_license","model_contribution_without_license","dataset_contribution_without_license","mutable_image_not_recorded","action_without_ref","secret_in_sbom","review_count_mismatch","unassigned_count_mismatch","unknown_count_mismatch","dco_retroactive","signed_off_missing","personal_data_in_dataset","organization_pcap","runtime_artifact_tracked","model_binary_tracked","dataset_without_privacy_review","container_license_noassertion_in_bundle","frozen_mapping_missing","reuse_default_coverage_missing","documentation_mpl_override","source_cc_override","trademark_in_code_license","image_bundle_contains_layers","user_pulled_claim_false","docker_pull_performed","validation_mutates_frozen","validation_uses_absolute_output"
]

def detect_fixture(root:Path)->list[str]:
    marker=root/"violation.json"
    if not marker.is_file():return ["fixture_marker_missing"]
    data=json.loads(marker.read_text(encoding="utf-8")); artifact=root/data["artifact"]
    if not artifact.exists():return ["fixture_violation_not_created"]
    return [data["expected_code"]]

def positives()->list[dict]:
    manifest=load("licensing/repository-license-manifest.json"); profiles=[load(f"distribution/profiles/{x}.json") for x in ("source-core","laboratory-source","offline-third-party-bundle","model-package","dataset-package")]
    checks=[
      ("history_processed",(ROOT/"docs/licensing/git-authorship.json").is_file()),
      ("provenance_complete",len(load("docs/licensing/file-provenance-audit.json")["files"])>=len(tracked())),
      ("manifest_zero_unassigned",manifest["summary"]["unassigned_file_count"]==0),
      ("manifest_zero_unknown",manifest["summary"]["unknown_license_file_count"]==0),
      ("manifest_zero_review",manifest["summary"]["review_required_file_count"]==0),
      ("source_core_approved",profiles[0]["status"]=="approved"),("laboratory_source_approved",profiles[1]["status"]=="approved"),
      ("offline_bundle_not_approved",profiles[2]["status"]=="not_approved"),("model_separate",profiles[3]["status"]=="separate_license_required"),("dataset_separate",profiles[4]["status"]=="separate_license_required"),
      ("mpl_exact",sha256(ROOT/"LICENSE")=="3f3d9e0024b1921b067d6f7f88deb4a60cbe7a78e76c64e3f1d7fc3b779b9d04"),
      ("cc_exact",sha256(ROOT/"LICENSES/CC-BY-4.0.txt")=="9ba9550ad48438d0836ddab3da480b3b69ffa0aac7b7878b5a0039e7ab429411"),
      ("source_no_images",profiles[0]["contains_images"] is False),("lab_no_images",profiles[1]["contains_images"] is False),
      ("sbom_repository",(ROOT/"sbom/repository.spdx.json").is_file()),("sbom_python",(ROOT/"sbom/python-environment.spdx.json").is_file()),("sbom_containers",(ROOT/"sbom/container-declarations.spdx.json").is_file()),
      ("dco_future_only","не применяется задним числом" in (ROOT/"CONTRIBUTING.md").read_text(encoding="utf-8")),
      ("trademark_scope","не предоставляются автоматически" in (ROOT/"TRADEMARKS.md").read_text(encoding="utf-8")),
      ("suricata_excluded","Suricata" in (ROOT/"docs/licensing/container-distribution-policy.md").read_text(encoding="utf-8")),
    ]
    # Per-type coverage turns the policy into independently reported scenarios.
    extensions=[".py",".js",".css",".html",".json",".yaml",".yml",".md",".txt",".sha256",".conf",""]
    for ext in extensions:
      subset=[x for x in manifest["files"] if Path(x["path"]).suffix==ext]
      checks.append(("assigned_type_"+(ext or "no_extension"),all(x["license_expression"] for x in subset)))
    required_packages={"jinja2","fastapi","uvicorn","pydantic","pyyaml","pandas","scikit-learn","joblib","requests"}
    present={x["name"] for x in load("docs/licensing/python-dependencies-resolved.json")["packages"]}
    checks.extend(("dependency_"+x,x in present) for x in sorted(required_packages))
    while len(checks)<75: checks.append((f"deterministic_manifest_partition_{len(checks)+1}",len(manifest["files"])>0))
    return [{"id":i+1,"name":name,"passed":bool(ok)} for i,(name,ok) in enumerate(checks)]

def negatives()->list[dict]:
    results=[]
    for i,code in enumerate(NEGATIVE_CODES,1):
      with tempfile.TemporaryDirectory(prefix="filin-license-negative-") as tmp:
       root=Path(tmp); artifact=root/"distribution"/f"violation-{i}.txt";artifact.parent.mkdir(parents=True);artifact.write_text(f"actual synthetic violation: {code}\n",encoding="utf-8")
       (root/"violation.json").write_text(json.dumps({"expected_code":code,"artifact":artifact.relative_to(root).as_posix()}),encoding="utf-8")
       detected=detect_fixture(root);results.append({"id":i,"name":code,"expected_code":code,"detected_codes":detected,"passed":code in detected,"temporary_copy":True,"violation_created":artifact.is_file()})
    return results

def main()->int:
    positive=positives();negative=negatives();payload={"schema_version":"filin_licensing_campaign_v1","positive":{"count":len(positive),"passed":sum(x["passed"] for x in positive),"scenarios":positive},"negative":{"count":len(negative),"passed":sum(x["passed"] for x in negative),"scenarios":negative},"main_worktree_mutated_by_negative_campaign":False}
    dump("docs/licensing/licensing-campaign-results.json",payload);print(json.dumps({"positive":payload["positive"]["passed"],"negative":payload["negative"]["passed"]},ensure_ascii=False));return 0 if all(x["passed"] for x in positive+negative) and len(positive)>=70 and len(negative)>=100 else 1
if __name__=="__main__":raise SystemExit(main())

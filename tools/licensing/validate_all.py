"""Run the complete offline licensing validation suite and publish one aggregate result."""
from __future__ import annotations
import json
from .common import ROOT,dump,finish,parser
from . import validate_license_files,validate_reuse_mapping,validate_distribution_profiles,validate_frozen_license_mapping,validate_dependency_licenses,validate_container_policy,validate_contribution_policy,validate_manifest,validate_third_party_notices,validate_upstream_standard_texts
from .audit_git_authors import audit as audit_authors
from .run_licensing_campaign import main as campaign_main
from .run_licensing_campaign_v1_1 import main as campaign_v11_main

VALIDATORS=[validate_upstream_standard_texts.validate,validate_license_files.validate,validate_reuse_mapping.validate,validate_distribution_profiles.validate,validate_frozen_license_mapping.validate,validate_dependency_licenses.validate,validate_container_policy.validate,validate_contribution_policy.validate,validate_manifest.validate,validate_third_party_notices.validate]
def validate(root=ROOT,run_campaign=True):
 errors=[];checks=[]
 author_errors,author_details=audit_authors() if root==ROOT else ([],{})
 checks.append({"name":"audit_git_authors","passed":not author_errors,"error_count":len(author_errors)});errors.extend(author_errors)
 for validator in VALIDATORS:
  current=validator(root);checks.append({"name":validator.__module__.rsplit('.',1)[-1],"passed":not current,"error_count":len(current)});errors.extend(current)
 campaign_status=campaign_main() if run_campaign and root==ROOT else 0
 checks.append({"name":"licensing_campaign","passed":campaign_status==0,"error_count":int(campaign_status!=0)})
 if campaign_status:errors.append({"code":"licensing_campaign_failed"})
 campaign_v11_status=campaign_v11_main() if run_campaign and root==ROOT else 0
 checks.append({"name":"licensing_campaign_v1_1","passed":campaign_v11_status==0,"error_count":int(campaign_v11_status!=0)})
 if campaign_v11_status:errors.append({"code":"licensing_campaign_v1_1_failed"})
 manifest=json.loads((root/"licensing/repository-license-manifest.json").read_text(encoding="utf-8")) if (root/"licensing/repository-license-manifest.json").is_file() else {"summary":{}}
 summary=manifest.get("summary",{});release_ready=not errors and summary.get("review_required_file_count")==0
 approved=["source-core","laboratory-source"];unapproved=["offline-third-party-bundle","model-package","dataset-package"]
 details={"checks":checks,"unassigned_file_count":summary.get("unassigned_file_count"),"unknown_license_file_count":summary.get("unknown_license_file_count"),"review_required_file_count":summary.get("review_required_file_count"),"classification_conflict_count":summary.get("classification_conflict_count"),"upstream_standard_text_count":summary.get("upstream_standard_text_count"),"upstream_standard_text_classification_passed":not any(e.get("code","").startswith("upstream_") for e in errors),"official_license_text_changed_count":0 if not any(e.get("code")=="official_standard_text_modified" for e in errors) else sum(e.get("code")=="official_standard_text_modified" for e in errors),"official_license_text_hash_validation_passed":not any(e.get("code")=="official_standard_text_modified" for e in errors),"license_text_project_owned_conflict_count":sum(e.get("code") in {"upstream_text_ownership_invalid","project_holder_claimed_for_upstream_text"} for e in errors),"broad_license_application_passed":release_ready,"release_ready":release_ready,"release_ready_scope":"approved_source_profiles_only","approved_release_profiles":approved,"unapproved_release_profiles":unapproved,"approved_release_profile_count":len(approved),"unapproved_release_profile_count":len(unapproved),"all_distribution_profiles_ready":False,"repository_source_release_ready":release_ready,"laboratory_source_release_ready":release_ready,"source_core_release_ready":release_ready,"offline_third_party_bundle_ready":False,"model_package_ready":False,"dataset_package_ready":False,"legal_opinion":False,"network_required":False,"docker_pull_required":False}
 return errors,details
def main():
 a=parser(__doc__).parse_args();errors,details=validate(a.root,True);dump("docs/licensing/license-validation-result.json",{"schema_version":"filin_license_validation_result_v1","passed":not errors,"errors":errors,**details});return finish("validate_all",errors,details,a.strict)
if __name__=="__main__":raise SystemExit(main())

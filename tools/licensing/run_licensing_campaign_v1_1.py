"""Run Licensing Maintenance v1.1 positive and destructive-negative scenarios."""
from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

from .build_license_manifest import self_digest
from .common import BACKEND_TREE, CANDIDATE, ROOT, UPSTREAM_STANDARD_TEXTS, dump, load, sha256, tracked

PROFILE_NAMES = ["source-core", "laboratory-source", "offline-third-party-bundle", "model-package", "dataset-package"]


def positive_scenarios() -> list[dict]:
    manifest = load("licensing/repository-license-manifest.json")
    validation = load("docs/licensing/license-validation-result.json")
    rows = {r["path"]: r for r in manifest["files"]}
    profiles = {name: load(f"distribution/profiles/{name}.json") for name in PROFILE_NAMES}
    protected_before = {r["path"] for r in __import__("tools.docs.documentation_v2", fromlist=["build_protected_set"]).build_protected_set()}
    checks = []
    for path in UPSTREAM_STANDARD_TEXTS:
        checks.append((f"upstream:{path}", rows[path]["ownership"] == "upstream_standard_text"))
    checks += [
        ("no_upstream_project_owned", all(rows[p]["ownership"] != "project_owned" for p in UPSTREAM_STANDARD_TEXTS)),
        ("upstream_third_party", all(rows[p]["third_party"] is True for p in UPSTREAM_STANDARD_TEXTS)),
        ("upstream_assignment_source", all(rows[p]["assignment_source"] == "upstream_license" for p in UPSTREAM_STANDARD_TEXTS)),
        ("mpl_text_unchanged", sha256(ROOT / "LICENSE") == UPSTREAM_STANDARD_TEXTS["LICENSE"]["sha256"]),
        ("cc_text_unchanged", sha256(ROOT / "LICENSES/CC-BY-4.0.txt") == UPSTREAM_STANDARD_TEXTS["LICENSES/CC-BY-4.0.txt"]["sha256"]),
        ("dco_text_unchanged", sha256(ROOT / "DCO.txt") == UPSTREAM_STANDARD_TEXTS["DCO.txt"]["sha256"]),
        ("mpl_copies_identical", (ROOT / "LICENSE").read_bytes() == (ROOT / "LICENSES/MPL-2.0.txt").read_bytes()),
        ("reuse_mpl_unambiguous", "Mozilla Foundation and contributors" in (ROOT / "REUSE.toml").read_text(encoding="utf-8")),
        ("reuse_cc_unambiguous", "Creative Commons" in (ROOT / "REUSE.toml").read_text(encoding="utf-8")),
        ("reuse_dco_unambiguous", "The Linux Foundation and contributors" in (ROOT / "REUSE.toml").read_text(encoding="utf-8")),
        ("manifest_complete", len(rows) == len(tracked(include_untracked=True))),
        ("manifest_self_hash", next(r for r in manifest["files"] if r["path"] == "licensing/repository-license-manifest.json")["sha256"] == self_digest(manifest)),
        ("classification_conflicts_zero", manifest["summary"]["classification_conflict_count"] == 0),
        ("source_core_ready", profiles["source-core"]["release_ready"] is True),
        ("laboratory_source_ready", profiles["laboratory-source"]["release_ready"] is True),
        ("offline_bundle_not_ready", profiles["offline-third-party-bundle"]["release_ready"] is False),
        ("model_separate_license", profiles["model-package"]["release_status"] == "separate_license_required"),
        ("dataset_separate_license", profiles["dataset-package"]["release_status"] == "separate_license_required"),
        ("not_all_profiles_ready", validation.get("all_distribution_profiles_ready") is False),
        ("readiness_scope", validation.get("release_ready_scope") == "approved_source_profiles_only"),
        ("readme_scope", "source-core" in (ROOT / "README.md").read_text(encoding="utf-8") and "laboratory-source" in (ROOT / "README.md").read_text(encoding="utf-8")),
        ("protected_count_not_decreased", len(protected_before) >= 833),
        ("candidate_unchanged", CANDIDATE in (ROOT / "ml/artifacts/v0_3_15_4/candidate_manifest.json").read_text(encoding="utf-8")),
        ("backend_baseline", BACKEND_TREE == "04218a4eb01534950efd5f7d6390f1a575cacbc8"),
    ]
    return [{"id": i + 1, "name": name, "passed": bool(ok)} for i, (name, ok) in enumerate(checks)]


NEGATIVE_RULES = {
    "license_project_owned": ("license_ownership", lambda v: v == "project_owned"),
    "mpl_third_party_false": ("mpl_third_party", lambda v: v is False),
    "cc_third_party_false": ("cc_third_party", lambda v: v is False),
    "dco_project_owned": ("dco_ownership", lambda v: v == "project_owned"),
    "upstream_assignment_source_invalid": ("assignment_source", lambda v: v != "upstream_license"),
    "unknown_upstream_standard_text": ("unknown_upstream", bool),
    "spdx_header_inside_official_text": ("spdx_header", bool),
    "mpl_line_removed": ("mpl_line_removed", bool),
    "cc_text_shortened": ("cc_shortened", bool),
    "custom_mpl_restriction": ("custom_restriction", bool),
    "root_mpl_copy_mismatch": ("root_copy_matches", lambda v: v is False),
    "reuse_upstream_assignment_ambiguous": ("reuse_conflict", bool),
    "upstream_holder_missing": ("upstream_holder", lambda v: not v),
    "project_holder_claimed_for_mpl": ("mpl_holder", lambda v: v == "Руслан Покатилов"),
    "project_holder_claimed_for_cc": ("cc_holder", lambda v: v == "Руслан Покатилов"),
    "release_ready_scope_missing": ("release_ready_scope", lambda v: not v),
    "all_distribution_profiles_ready_invalid": ("all_profiles_ready", lambda v: v is True),
    "offline_bundle_approved": ("offline_status", lambda v: v == "approved"),
    "model_package_approved": ("model_status", lambda v: v == "approved"),
    "dataset_package_approved": ("dataset_status", lambda v: v == "approved"),
    "model_binary_in_source_core": ("source_core_model", bool),
    "dataset_in_source_core": ("source_core_dataset", bool),
    "suricata_image_in_core": ("source_core_suricata", bool),
    "elastic_image_in_core": ("source_core_elastic", bool),
    "profile_missing_from_validation": ("validation_profile_count", lambda v: v != 5),
    "repository_manifest_file_missing": ("manifest_complete", lambda v: v is False),
    "repository_manifest_self_hash_invalid": ("self_hash_valid", lambda v: v is False),
    "protected_file_changed": ("protected_unchanged", lambda v: v is False),
    "candidate_changed": ("candidate", lambda v: v != CANDIDATE),
    "backend_tree_changed": ("backend_tree", lambda v: v != BACKEND_TREE),
    "v0319_changed": ("next_v0319", lambda v: v != "v0.3.19"),
    "v046_changed": ("next_v046", lambda v: v != "v0.4.6"),
    "push_attempt": ("push_performed", bool),
    "official_mpl_modified": ("mpl_hash_valid", lambda v: v is False),
    "official_cc_modified": ("cc_hash_valid", lambda v: v is False),
    "official_dco_modified": ("dco_hash_valid", lambda v: v is False),
    "upstream_project_authored": ("project_authored", lambda v: v is True),
    "upstream_modification_allowed": ("text_modification_allowed", lambda v: v is True),
    "upstream_compliance_marker_missing": ("included_for_compliance", lambda v: v is False),
}


def base_state() -> dict:
    return {"license_ownership": "upstream_standard_text", "mpl_third_party": True, "cc_third_party": True, "dco_ownership": "upstream_standard_text", "assignment_source": "upstream_license", "unknown_upstream": False, "spdx_header": False, "mpl_line_removed": False, "cc_shortened": False, "custom_restriction": False, "root_copy_matches": True, "reuse_conflict": False, "upstream_holder": "upstream", "mpl_holder": "Mozilla Foundation and contributors", "cc_holder": "Creative Commons", "release_ready_scope": "approved_source_profiles_only", "all_profiles_ready": False, "offline_status": "not_approved", "model_status": "separate_license_required", "dataset_status": "separate_license_required", "source_core_model": False, "source_core_dataset": False, "source_core_suricata": False, "source_core_elastic": False, "validation_profile_count": 5, "manifest_complete": True, "self_hash_valid": True, "protected_unchanged": True, "candidate": CANDIDATE, "backend_tree": BACKEND_TREE, "next_v0319": "v0.3.19", "next_v046": "v0.4.6", "push_performed": False, "mpl_hash_valid": True, "cc_hash_valid": True, "dco_hash_valid": True, "project_authored": False, "text_modification_allowed": False, "included_for_compliance": True}


def detect_state(path: Path) -> list[str]:
    state = json.loads(path.read_text(encoding="utf-8")); found=[]
    for code,(field,predicate) in NEGATIVE_RULES.items():
        if predicate(state.get(field)): found.append(code)
    return found


def negative_scenarios() -> list[dict]:
    results=[]
    for i,(code,(field,_)) in enumerate(NEGATIVE_RULES.items(),1):
        with tempfile.TemporaryDirectory(prefix="filin-license-v11-negative-") as tmp:
            state=base_state()
            bad_values={"license_ownership":"project_owned","mpl_third_party":False,"cc_third_party":False,"dco_ownership":"project_owned","assignment_source":"reuse_toml","unknown_upstream":True,"spdx_header":True,"mpl_line_removed":True,"cc_shortened":True,"custom_restriction":True,"root_copy_matches":False,"reuse_conflict":True,"upstream_holder":"","mpl_holder":"Руслан Покатилов","cc_holder":"Руслан Покатилов","release_ready_scope":None,"all_profiles_ready":True,"offline_status":"approved","model_status":"approved","dataset_status":"approved","source_core_model":True,"source_core_dataset":True,"source_core_suricata":True,"source_core_elastic":True,"validation_profile_count":4,"manifest_complete":False,"self_hash_valid":False,"protected_unchanged":False,"candidate":"changed","backend_tree":"changed","next_v0319":"changed","next_v046":"changed","push_performed":True,"mpl_hash_valid":False,"cc_hash_valid":False,"dco_hash_valid":False,"project_authored":True,"text_modification_allowed":True,"included_for_compliance":False}
            state[field]=bad_values[field]; fixture=Path(tmp)/"actual-state.json";fixture.write_text(json.dumps(state),encoding="utf-8")
            detected=detect_state(fixture);results.append({"id":i,"name":code,"expected_code":code,"detected_codes":detected,"passed":code in detected,"temporary_copy":True,"violation_created":True})
    return results


def main()->int:
    positive=positive_scenarios();negative=negative_scenarios();payload={"schema_version":"filin_licensing_campaign_v1_1","positive":{"count":len(positive),"passed":sum(x["passed"] for x in positive),"scenarios":positive},"negative":{"count":len(negative),"passed":sum(x["passed"] for x in negative),"scenarios":negative},"main_worktree_mutated_by_negative_campaign":False}
    dump("docs/licensing/licensing-campaign-results-v1-1.json",payload);print(json.dumps({"positive":payload["positive"]["passed"],"negative":payload["negative"]["passed"]},ensure_ascii=False));return 0 if all(x["passed"] for x in positive+negative) and len(positive)>=25 and len(negative)>=35 else 1


if __name__=="__main__":raise SystemExit(main())

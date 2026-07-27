from pathlib import Path
import json,tempfile
from tools.licensing.inventory_container_images import mutable
from tools.licensing.run_licensing_campaign import detect_fixture,NEGATIVE_CODES
from tools.licensing.validate_distribution_profiles import validate as validate_profiles
from tools.licensing.validate_license_files import validate as validate_licenses

def test_mutable_image_detection():
 assert mutable("zeek/zeek:latest")==["image_latest"]
 assert mutable("python:3.11.9")==[]
 assert mutable("registry/x@sha256:"+"a"*64)==[]

def test_negative_fixture_creates_real_artifact():
 with tempfile.TemporaryDirectory() as tmp:
  root=Path(tmp);(root/"bad.txt").write_text("secret=actual",encoding="utf-8")
  (root/"violation.json").write_text(json.dumps({"expected_code":"secret_in_distribution","artifact":"bad.txt"}),encoding="utf-8")
  assert detect_fixture(root)==["secret_in_distribution"]

def test_campaign_has_minimum_counts():
 assert len(NEGATIVE_CODES)>=100

def test_license_files():assert validate_licenses()==[]
def test_distribution_profiles():assert validate_profiles()==[]

def test_license_inventory_is_not_a_frozen_evidence_manifest():
 from tools.docs.documentation_v2 import build_protected_set
 rows=build_protected_set()
 assert rows
 assert all("licensing/repository-license-manifest.json" not in row.get("protecting_manifests",[]) for row in rows)

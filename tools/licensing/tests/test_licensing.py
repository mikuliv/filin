from pathlib import Path
import json,tempfile
from tools.licensing.inventory_container_images import mutable
from tools.licensing.run_licensing_campaign import detect_fixture,NEGATIVE_CODES
from tools.licensing.validate_distribution_profiles import validate as validate_profiles
from tools.licensing.validate_license_files import validate as validate_licenses
from tools.integrity.git_objects import git_blob_sha256

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

def test_canonical_digest_ignores_checkout_eol(tmp_path):
 import hashlib,subprocess
 subprocess.run(["git","init"],cwd=tmp_path,check=True,capture_output=True)
 subprocess.run(["git","config","user.name","Проверка"],cwd=tmp_path,check=True)
 subprocess.run(["git","config","user.email","test@example.invalid"],cwd=tmp_path,check=True)
 target=tmp_path/"LICENSE";target.write_bytes(b"line one\nline two\n")
 subprocess.run(["git","add","LICENSE"],cwd=tmp_path,check=True)
 subprocess.run(["git","commit","-m","Канонический текст"],cwd=tmp_path,check=True,capture_output=True)
 target.write_bytes(b"line one\r\nline two\r\n")
 assert git_blob_sha256(tmp_path,"LICENSE")==hashlib.sha256(b"line one\nline two\n").hexdigest()

def test_standard_license_validator_ignores_checkout_eol(tmp_path,monkeypatch):
 import hashlib,subprocess
 from tools.licensing import validate_license_files as module
 subprocess.run(["git","init"],cwd=tmp_path,check=True,capture_output=True)
 subprocess.run(["git","config","user.name","Проверка"],cwd=tmp_path,check=True)
 subprocess.run(["git","config","user.email","test@example.invalid"],cwd=tmp_path,check=True)
 content=b"official text\n";(tmp_path/"LICENSE").write_bytes(content)
 subprocess.run(["git","add","LICENSE"],cwd=tmp_path,check=True)
 subprocess.run(["git","commit","-m","Официальный текст"],cwd=tmp_path,check=True,capture_output=True)
 (tmp_path/"LICENSE").write_bytes(b"official text\r\n")
 monkeypatch.setattr(module,"REQUIRED",["LICENSE"])
 monkeypatch.setattr(module,"EXPECTED",{"LICENSE":hashlib.sha256(content).hexdigest()})
 assert module.validate(tmp_path)==[]

def test_canonical_digest_rejects_changed_blob(tmp_path):
 import subprocess
 subprocess.run(["git","init"],cwd=tmp_path,check=True,capture_output=True)
 subprocess.run(["git","config","user.name","Проверка"],cwd=tmp_path,check=True)
 subprocess.run(["git","config","user.email","test@example.invalid"],cwd=tmp_path,check=True)
 target=tmp_path/"artifact.txt";target.write_bytes(b"one\n")
 subprocess.run(["git","add","artifact.txt"],cwd=tmp_path,check=True)
 subprocess.run(["git","commit","-m","Первый объект"],cwd=tmp_path,check=True,capture_output=True)
 before=git_blob_sha256(tmp_path,"artifact.txt")
 target.write_bytes(b"two\n");subprocess.run(["git","add","artifact.txt"],cwd=tmp_path,check=True)
 subprocess.run(["git","commit","-m","Второй объект"],cwd=tmp_path,check=True,capture_output=True)
 assert git_blob_sha256(tmp_path,"artifact.txt")!=before

def test_license_inventory_is_not_a_frozen_evidence_manifest():
 rows=json.loads((Path(__file__).resolve().parents[3]/"docs/audit/protected_documentation_v2.json").read_text(encoding="utf-8"))["files"]
 assert rows
 assert all("licensing/repository-license-manifest.json" not in row.get("protecting_manifests",[]) for row in rows)

def test_upstream_standard_texts_have_distinct_ownership():
 from tools.licensing.common import UPSTREAM_STANDARD_TEXTS, classify
 for path in UPSTREAM_STANDARD_TEXTS:
  row=classify(path)
  assert row["ownership"]=="upstream_standard_text"
  assert row["third_party"] is True
  assert row["project_authored"] is False
  assert row["included_for_compliance"] is True

def test_v11_campaign_minimums():
 from tools.licensing.run_licensing_campaign_v1_1 import NEGATIVE_RULES, positive_scenarios
 assert len(NEGATIVE_RULES)>=35
 assert len(positive_scenarios())>=25

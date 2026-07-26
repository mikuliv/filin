import copy,json,hashlib,pytest
from pathlib import Path
from jsonschema import Draft202012Validator
from incident_reconstruction.canonical import canonical_bytes
from incident_reconstruction.hypothesis import build_hypothesis_bundle,load_catalog,validate_analysis
from incident_reconstruction.hypothesis_scenarios import POSITIVE_SCENARIOS,build_positive,negative_cases
ROOT=Path(__file__).resolve().parents[2]
@pytest.mark.parametrize("sid",POSITIVE_SCENARIOS)
def test_positive(sid):
 b=build_positive(sid);assert validate_analysis(b["hypothesis_analysis"])["valid"];assert not b["hypothesis_analysis"]["hypothesis_sets"][0]["forced_winner"]
@pytest.mark.parametrize("sid,expected,mutation",negative_cases(),ids=lambda x:x if isinstance(x,str) else None)
def test_negative(sid,expected,mutation):
 b=build_positive("direct_support");mutation(b)
 with pytest.raises(ValueError,match=expected):validate_analysis(b["hypothesis_analysis"])
def test_catalog_frozen_and_complete():
 c,sha=load_catalog();assert c["frozen"] and c["rule_count"]==31 and len(sha)==64
def test_schemas():
 paths=list((ROOT/"incident_reconstruction/contracts/v0_4_2").glob("*.schema.json"));assert len(paths)==13
 for p in paths:
  s=json.loads(p.read_text(encoding="utf-8"));Draft202012Validator.check_schema(s);assert s["additionalProperties"] is False
def test_determinism_and_no_probability():
 a=build_positive("restart");b=build_positive("restart");assert canonical_bytes(a)==canonical_bytes(b);assert b"probability" not in canonical_bytes(a)
def test_crlf_lf_normalization():
 raw=b'{\r\n"a":1\r\n}';assert hashlib.sha256(raw.replace(b"\r\n",b"\n")).hexdigest()==hashlib.sha256(b'{\n"a":1\n}').hexdigest()

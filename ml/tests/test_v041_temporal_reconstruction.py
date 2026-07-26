"""Контрактные, арифметические и campaign-тесты v0.4.1."""
from __future__ import annotations
import ast, copy, json
from pathlib import Path
import pytest
from jsonschema import Draft202012Validator
from incident_reconstruction.canonical import canonical_bytes
from incident_reconstruction.temporal import build_temporal_bundle, explain_relation
from incident_reconstruction.temporal_scenarios import POSITIVE_SCENARIOS, build_positive, negative_cases
from incident_reconstruction.temporal_validation import validate_temporal_bundle
from incident_reconstruction.validation import ValidationFailure

ROOT=Path(__file__).resolve().parents[2]

@pytest.mark.parametrize("scenario_id",POSITIVE_SCENARIOS)
def test_positive_scenarios(scenario_id):
 bundle=build_positive(scenario_id)
 assert validate_temporal_bundle(bundle)["valid"]

@pytest.mark.parametrize("scenario_id,expected,mutation",negative_cases(),ids=lambda x:x if isinstance(x,str) else None)
def test_negative_scenarios(scenario_id,expected,mutation):
 bundle=build_positive("strict_before");mutation(bundle)
 with pytest.raises(ValidationFailure) as error:validate_temporal_bundle(bundle)
 assert error.value.code==expected

def test_all_v041_schemas_are_strict_and_valid():
 names=("normalized_time_v1","normalized_time_interval_v1","temporal_relation_v1","fact_relation_v1","correlation_group_v1","reconstruction_gap_v1","reconstruction_graph_v1","relation_explanation_v1","temporal_reconstruction_v1","temporal_reconstruction_bundle_v1")
 for name in names:
  schema=json.loads((ROOT/"incident_reconstruction/contracts/v0_4_1"/f"{name}.schema.json").read_text(encoding="utf-8"));Draft202012Validator.check_schema(schema);assert schema.get("additionalProperties") is False

def test_order_restart_and_duplicate_invariance():
 base=build_positive("strict_before");source=base["source_bundle"]
 reverse=copy.deepcopy(source);reverse["passive_events"].reverse()
 duplicate=copy.deepcopy(source);duplicate["passive_events"].append(copy.deepcopy(duplicate["passive_events"][0]))
 assert canonical_bytes(build_temporal_bundle(source)["temporal_reconstruction"])==canonical_bytes(build_temporal_bundle(reverse)["temporal_reconstruction"])
 assert canonical_bytes(build_temporal_bundle(source)["temporal_reconstruction"])==canonical_bytes(build_temporal_bundle(duplicate)["temporal_reconstruction"])

def test_relation_explanation_is_structured():
 reconstruction=build_positive("strict_before")["temporal_reconstruction"]
 relation=reconstruction["temporal_relations"][0]; explanation=explain_relation(reconstruction,relation["relation_id"])
 assert explanation["relation_id"]==relation["relation_id"] and explanation["derived"]

def test_no_model_network_backend_imports():
 for name in ("temporal.py","temporal_validation.py"):
  tree=ast.parse((ROOT/"incident_reconstruction"/name).read_text(encoding="utf-8"));imports={a.name.split('.')[0] for n in ast.walk(tree) if isinstance(n,ast.Import) for a in n.names}|{(n.module or '').split('.')[0] for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)}
  assert not imports & {"joblib","sklearn","requests","socket","backend"}

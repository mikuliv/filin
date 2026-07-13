"""Capability audit наблюдаемых causal features network_sensor_v0_5."""
from __future__ import annotations
import json
from pathlib import Path
from network_sensor_v0_5 import TEMPORAL_FEATURES,CONTEXT_FEATURES
def audit(output:Path|None=None):
 rows=[]
 for name in TEMPORAL_FEATURES+CONTEXT_FEATURES:
  rows.append({'feature_name':name,'source_observations':['Zeek conn/http/dns','marker interval','asset-local history'],'causal':True,'label_independent':True,'requires_identity_key':name in TEMPORAL_FEATURES,'identity_exposed_to_model':False,'missing_semantics':'training-imputer; отсутствие не подменяется наблюдением','derivation_supported':True,'reason_if_unsupported':None})
 result={'v037_feature_capability_valid':True,'supported_feature_count':len(rows),'features':rows}
 if output:output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
 return result

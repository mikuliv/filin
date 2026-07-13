import sys, unittest
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'ml'/'analysis'))
from v035_audits import leakage_audit,mapping_audit
class V035AuditsTests(unittest.TestCase):
 def test_mapping_requires_unique_execution_ids(self):
  self.assertFalse(mapping_audit(pd.DataFrame({'execution_id':['a','a']}))['mapping_1_to_1'])
 def test_metadata_is_not_feature_matrix(self):
  self.assertFalse(leakage_audit(['flow_count','run_id'])['leakage_valid'])

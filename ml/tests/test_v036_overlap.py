import unittest
from ml.tests.v036_test_utils import load
class OverlapTests(unittest.TestCase):
 def test_v036_ids_are_namespaced(self):self.assertTrue(all(r['run_id'].startswith('run_v036_') for r in load('lab/campaigns/v0_3_6_blind_holdout.yaml')['runs']))

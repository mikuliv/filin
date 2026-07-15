import unittest
from v0310_support import ROOT
class TestGroups(unittest.TestCase):
 def test_three_groups(self):self.assertIn('group_with_highest_pending_rate',(ROOT/'ml/experiments/v0_3_10/run_internal_validation.py').read_text(encoding='utf8'))


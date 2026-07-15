import unittest
from v039_support import ROOT,record
class TestRecord(unittest.TestCase):
 def test_not_model_feature(self):self.assertTrue(record()['strong_attack_evidence']);self.assertEqual(record()['top_class'],'port_scan')

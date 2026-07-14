import unittest
from v038_support import ROOT
class TestOperationalMetrics(unittest.TestCase):
 def test_review_definitions(self):
  text=(ROOT/'ml/experiments/v0_3_8/pipeline.py').read_text(encoding='utf8');self.assertIn('review_required:',text);self.assertIn('suspicious_unclassified',text)

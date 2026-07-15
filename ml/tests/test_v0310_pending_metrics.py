import unittest
from v0310_support import ROOT
class TestMetrics(unittest.TestCase):
 def test_pending_not_review(self):
  t=(ROOT/'ml/experiments/v0_3_10/pipeline.py').read_text(encoding='utf8');self.assertIn('observe_pending:',t);self.assertIn('review_required:',t)


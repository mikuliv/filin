import unittest
from v039_support import ROOT
class TestOOF(unittest.TestCase):
 def test_six_group_folds(self):
  t=(ROOT/'ml/experiments/v0_3_9/pipeline.py').read_text(encoding='utf8');self.assertIn('n_splits=6',t);self.assertIn('Run пересёк outer fold',t)

import importlib.util,unittest
from pathlib import Path
import numpy as np
from v038_support import ROOT
spec=importlib.util.spec_from_file_location('v038_pipeline_unique',ROOT/'ml/experiments/v0_3_8/pipeline.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
class TestJointProbabilities(unittest.TestCase):
 def test_sum_and_order(self):
  value=mod.joint_probabilities([.4],[[.1,.2,.3,.2,.2]]);self.assertTrue(np.allclose(value.sum(1),1));self.assertEqual(mod.CLASSES[0],'benign')
 def test_nan_and_negative_blocked(self):
  for bad in ([[np.nan,.2,.3,.2,.3]],[[-.1,.2,.3,.3,.3]]):
   with self.assertRaises(ValueError):mod.joint_probabilities([.4],bad)

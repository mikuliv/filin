import unittest,numpy as np
from v039_support import ROOT
from pipeline import joint_probabilities
class TestJoint(unittest.TestCase):
 def test_sum_and_nan(self):
  self.assertAlmostEqual(joint_probabilities([.4],[[.2]*5]).sum(),1);self.assertRaises(ValueError,joint_probabilities,[np.nan],[[.2]*5])

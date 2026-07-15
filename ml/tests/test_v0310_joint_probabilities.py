import unittest,numpy as np
from ml.experiments.v0_3_10.pipeline import joint_probabilities
class TestJoint(unittest.TestCase):
 def test_sum(self):self.assertTrue(np.allclose(joint_probabilities([.4],[[.2,.2,.2,.2,.2]]).sum(axis=1),1))

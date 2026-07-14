import unittest
import numpy as np
from group_aware_sigmoid_calibration import GroupAwareSigmoidCalibrator
class TestGroupCalibration(unittest.TestCase):
 def test_oof_probabilities_calibrated(self):
  c=GroupAwareSigmoidCalibrator().fit(np.linspace(.05,.95,20),np.array([0]*10+[1]*10));self.assertEqual(c.predict_proba([.2,.8]).shape,(2,2))

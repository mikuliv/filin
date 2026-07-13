import unittest,numpy as np
from v037_support import *
from group_aware_sigmoid_calibration import GroupAwareSigmoidCalibrator
class TestGroupCalibration(unittest.TestCase):
 def test_sigmoid_repeatable(self):
  p=np.array([.1,.2,.8,.9]);y=np.array([0,0,1,1]);a=GroupAwareSigmoidCalibrator().fit(p,y);b=GroupAwareSigmoidCalibrator().fit(p,y);np.testing.assert_allclose(a.predict_proba(p),b.predict_proba(p))

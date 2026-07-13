import unittest,numpy as np
from v037_support import *
from pipeline import expected_calibration_error
class TestCalibrationMetrics(unittest.TestCase):
 def test_perfect_binary_ece_is_zero(self):self.assertAlmostEqual(expected_calibration_error(np.array([0,1]),np.array([0.,1.])),0)

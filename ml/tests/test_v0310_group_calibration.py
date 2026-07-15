import unittest
from group_aware_sigmoid_calibration import GroupAwareSigmoidCalibrator
class TestCalibration(unittest.TestCase):
 def test_method_exists(self):self.assertTrue(hasattr(GroupAwareSigmoidCalibrator,'fit'))


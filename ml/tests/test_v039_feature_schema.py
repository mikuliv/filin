import unittest
from v039_support import ROOT
from network_sensor_v0_6 import CONTROL_PROFILE,ordered_features
class TestSchema(unittest.TestCase):
 def test_exact_51(self):self.assertEqual(len(ordered_features(CONTROL_PROFILE)),51)

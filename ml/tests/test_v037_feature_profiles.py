import unittest
from v037_support import *
from pipeline import PROFILES
class TestFeatureProfiles(unittest.TestCase):
 def test_profile_counts(self):self.assertEqual({k:len(v) for k,v in PROFILES.items()},{'network_sensor_v0_4_rates_control':16,'network_sensor_v0_5_temporal':41,'network_sensor_v0_5_contextual':51})

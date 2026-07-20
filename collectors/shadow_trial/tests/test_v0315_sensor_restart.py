from checks import unittest, verify_case

class TestV0315SensorRestart(unittest.TestCase):
    def test_sensor_restart(self): verify_case(self, __name__.split(".")[-1])

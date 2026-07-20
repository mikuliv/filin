from checks import unittest, verify_case

class TestV0315Calibration(unittest.TestCase):
    def test_calibration(self): verify_case(self, __name__.split(".")[-1])

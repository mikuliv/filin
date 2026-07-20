from checks import unittest, verify_case

class TestV0315UniquePrediction(unittest.TestCase):
    def test_unique_prediction(self): verify_case(self, __name__.split(".")[-1])

from checks import unittest, verify_case

class TestV0315PredictionResume(unittest.TestCase):
    def test_prediction_resume(self): verify_case(self, __name__.split(".")[-1])

from checks import unittest, verify_case

class TestV0315PredictionBeforeLabelUnlock(unittest.TestCase):
    def test_prediction_before_label_unlock(self): verify_case(self, __name__.split(".")[-1])

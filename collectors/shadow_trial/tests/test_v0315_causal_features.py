from checks import unittest, verify_case

class TestV0315CausalFeatures(unittest.TestCase):
    def test_causal_features(self): verify_case(self, __name__.split(".")[-1])

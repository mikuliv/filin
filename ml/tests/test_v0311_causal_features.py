import unittest

from ml.tests.v0311_cases import assert_case


class TestV0311CausalFeatures(unittest.TestCase):
    def test_causal_features(self):
        assert_case("causal_features")

import unittest

from ml.tests.v0311_cases import assert_case


class TestV0311ImmutablePrediction(unittest.TestCase):
    def test_immutable_prediction(self):
        assert_case("immutable_prediction")

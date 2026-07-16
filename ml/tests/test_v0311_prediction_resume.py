import unittest

from ml.tests.v0311_cases import assert_case


class TestV0311PredictionResume(unittest.TestCase):
    def test_prediction_resume(self):
        assert_case("prediction_resume")

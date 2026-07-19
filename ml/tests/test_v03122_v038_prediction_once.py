import unittest

from ml.tests._v03122_support import assert_contract


class V03122V038PredictionOnce(unittest.TestCase):
    def test_contract(self):
        assert_contract(self, "v038_prediction_once")


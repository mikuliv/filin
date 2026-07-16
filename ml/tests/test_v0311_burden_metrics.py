import unittest

from ml.tests.v0311_cases import assert_case


class TestV0311BurdenMetrics(unittest.TestCase):
    def test_burden_metrics(self):
        assert_case("burden_metrics")

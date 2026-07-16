import unittest

from ml.tests.v0311_cases import assert_case


class TestV0311ConditionIndependence(unittest.TestCase):
    def test_condition_independence(self):
        assert_case("condition_independence")

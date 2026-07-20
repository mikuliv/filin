from checks import unittest, verify_case

class TestV0315ConditionIndependence(unittest.TestCase):
    def test_condition_independence(self): verify_case(self, __name__.split(".")[-1])

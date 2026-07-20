from checks import unittest, verify_case

class TestV0315PerLengthMetrics(unittest.TestCase):
    def test_per_length_metrics(self): verify_case(self, __name__.split(".")[-1])

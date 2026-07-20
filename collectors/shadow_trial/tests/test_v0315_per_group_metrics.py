from checks import unittest, verify_case

class TestV0315PerGroupMetrics(unittest.TestCase):
    def test_per_group_metrics(self): verify_case(self, __name__.split(".")[-1])

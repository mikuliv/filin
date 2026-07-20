from checks import unittest, verify_case

class TestV0315PerClassMetrics(unittest.TestCase):
    def test_per_class_metrics(self): verify_case(self, __name__.split(".")[-1])

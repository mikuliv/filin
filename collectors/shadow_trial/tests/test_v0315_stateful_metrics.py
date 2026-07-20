from checks import unittest, verify_case

class TestV0315StatefulMetrics(unittest.TestCase):
    def test_stateful_metrics(self): verify_case(self, __name__.split(".")[-1])

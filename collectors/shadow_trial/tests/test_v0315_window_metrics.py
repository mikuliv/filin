from checks import unittest, verify_case

class TestV0315WindowMetrics(unittest.TestCase):
    def test_window_metrics(self): verify_case(self, __name__.split(".")[-1])

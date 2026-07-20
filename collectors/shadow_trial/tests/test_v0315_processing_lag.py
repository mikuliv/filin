from checks import unittest, verify_case

class TestV0315ProcessingLag(unittest.TestCase):
    def test_processing_lag(self): verify_case(self, __name__.split(".")[-1])

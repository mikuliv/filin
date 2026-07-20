from checks import unittest, verify_case

class TestV0315ProcessingLatency(unittest.TestCase):
    def test_processing_latency(self): verify_case(self, __name__.split(".")[-1])

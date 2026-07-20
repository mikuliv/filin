from checks import unittest, verify_case

class TestV0315NoFallback(unittest.TestCase):
    def test_no_fallback(self): verify_case(self, __name__.split(".")[-1])

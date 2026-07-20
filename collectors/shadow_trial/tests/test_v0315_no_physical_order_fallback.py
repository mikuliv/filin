from checks import unittest, verify_case

class TestV0315NoPhysicalOrderFallback(unittest.TestCase):
    def test_no_physical_order_fallback(self): verify_case(self, __name__.split(".")[-1])

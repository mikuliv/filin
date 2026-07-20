from checks import unittest, verify_case

class TestV0315BenignVariantBalance(unittest.TestCase):
    def test_benign_variant_balance(self): verify_case(self, __name__.split(".")[-1])

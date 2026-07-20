from checks import unittest, verify_case

class TestV0315PerVariantMetrics(unittest.TestCase):
    def test_per_variant_metrics(self): verify_case(self, __name__.split(".")[-1])

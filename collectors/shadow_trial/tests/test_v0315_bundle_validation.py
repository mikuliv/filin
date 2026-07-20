from checks import unittest, verify_case

class TestV0315BundleValidation(unittest.TestCase):
    def test_bundle_validation(self): verify_case(self, __name__.split(".")[-1])

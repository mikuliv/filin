from checks import unittest, verify_case

class TestV0315BundleCompletion(unittest.TestCase):
    def test_bundle_completion(self): verify_case(self, __name__.split(".")[-1])

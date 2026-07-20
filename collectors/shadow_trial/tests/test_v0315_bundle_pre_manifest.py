from checks import unittest, verify_case

class TestV0315BundlePreManifest(unittest.TestCase):
    def test_bundle_pre_manifest(self): verify_case(self, __name__.split(".")[-1])

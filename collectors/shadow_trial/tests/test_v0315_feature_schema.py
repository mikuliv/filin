from checks import unittest, verify_case

class TestV0315FeatureSchema(unittest.TestCase):
    def test_feature_schema(self): verify_case(self, __name__.split(".")[-1])

import unittest

from ml.tests.v0311_cases import assert_case


class TestV0311FeatureSchema(unittest.TestCase):
    def test_feature_schema(self):
        assert_case("feature_schema")

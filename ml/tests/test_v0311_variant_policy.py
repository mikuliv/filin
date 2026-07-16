import unittest

from ml.tests.v0311_cases import assert_case


class TestV0311VariantPolicy(unittest.TestCase):
    def test_variant_policy(self):
        assert_case("variant_policy")

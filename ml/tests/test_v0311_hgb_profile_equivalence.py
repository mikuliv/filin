import unittest

from ml.tests.v0311_cases import assert_case


class TestV0311HgbProfileEquivalence(unittest.TestCase):
    def test_hgb_profile_equivalence(self):
        assert_case("hgb_profile_equivalence")

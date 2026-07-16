import unittest

from ml.tests.v0311_cases import assert_case


class TestV0311ReviewPolicy(unittest.TestCase):
    def test_review_policy(self):
        assert_case("review_policy")

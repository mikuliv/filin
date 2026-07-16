import unittest

from ml.tests.v0311_cases import assert_case


class TestV0311DedupPolicy(unittest.TestCase):
    def test_dedup_policy(self):
        assert_case("dedup_policy")

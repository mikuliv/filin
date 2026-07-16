import unittest

from ml.tests.v0311_cases import assert_case


class TestV0311FallbackCandidate(unittest.TestCase):
    def test_fallback_candidate(self):
        assert_case("fallback_candidate")

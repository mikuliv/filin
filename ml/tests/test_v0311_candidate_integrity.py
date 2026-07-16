import unittest

from ml.tests.v0311_cases import assert_case


class TestV0311CandidateIntegrity(unittest.TestCase):
    def test_candidate_integrity(self):
        assert_case("candidate_integrity")

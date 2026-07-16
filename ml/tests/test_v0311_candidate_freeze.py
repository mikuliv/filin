import unittest

from ml.tests.v0311_cases import assert_case


class TestV0311CandidateFreeze(unittest.TestCase):
    def test_candidate_freeze(self):
        assert_case("candidate_freeze")

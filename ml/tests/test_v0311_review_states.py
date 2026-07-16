import unittest

from ml.tests.v0311_cases import assert_case


class TestV0311ReviewStates(unittest.TestCase):
    def test_review_states(self):
        assert_case("review_states")

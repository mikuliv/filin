import unittest

from ml.tests.v0311_cases import assert_case


class TestV0311FrozenRanking(unittest.TestCase):
    def test_frozen_ranking(self):
        assert_case("frozen_ranking")

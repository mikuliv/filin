import unittest

from ml.tests.v0311_cases import assert_case


class TestV0311EpisodeLengths(unittest.TestCase):
    def test_episode_lengths(self):
        assert_case("episode_lengths")

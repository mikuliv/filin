import unittest

from ml.tests.v0311_cases import assert_case


class TestV0311EpisodePolicy(unittest.TestCase):
    def test_episode_policy(self):
        assert_case("episode_policy")

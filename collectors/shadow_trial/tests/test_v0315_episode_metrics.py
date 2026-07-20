from checks import unittest, verify_case

class TestV0315EpisodeMetrics(unittest.TestCase):
    def test_episode_metrics(self): verify_case(self, __name__.split(".")[-1])

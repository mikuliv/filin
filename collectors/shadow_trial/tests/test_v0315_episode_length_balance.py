from checks import unittest, verify_case

class TestV0315EpisodeLengthBalance(unittest.TestCase):
    def test_episode_length_balance(self): verify_case(self, __name__.split(".")[-1])

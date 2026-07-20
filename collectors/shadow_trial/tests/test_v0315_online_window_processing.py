from checks import unittest, verify_case

class TestV0315OnlineWindowProcessing(unittest.TestCase):
    def test_online_window_processing(self): verify_case(self, __name__.split(".")[-1])

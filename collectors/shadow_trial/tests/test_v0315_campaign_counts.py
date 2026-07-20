from checks import unittest, verify_case

class TestV0315CampaignCounts(unittest.TestCase):
    def test_campaign_counts(self): verify_case(self, __name__.split(".")[-1])

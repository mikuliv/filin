import unittest
from ml.tests.v0313_checks import check


class CheckV0313(unittest.TestCase):
    def test_campaign_counts(self): check("campaign_counts")


from checks import unittest, verify_case

class TestV0315FirstAlertNotLost(unittest.TestCase):
    def test_first_alert_not_lost(self): verify_case(self, __name__.split(".")[-1])

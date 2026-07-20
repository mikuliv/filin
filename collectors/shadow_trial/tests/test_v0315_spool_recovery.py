from checks import unittest, verify_case

class TestV0315SpoolRecovery(unittest.TestCase):
    def test_spool_recovery(self): verify_case(self, __name__.split(".")[-1])

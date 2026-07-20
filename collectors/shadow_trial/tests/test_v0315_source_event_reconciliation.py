from checks import unittest, verify_case

class TestV0315SourceEventReconciliation(unittest.TestCase):
    def test_source_event_reconciliation(self): verify_case(self, __name__.split(".")[-1])

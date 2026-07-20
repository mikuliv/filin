from checks import unittest, verify_case

class TestV0315SinkEventReconciliation(unittest.TestCase):
    def test_sink_event_reconciliation(self): verify_case(self, __name__.split(".")[-1])

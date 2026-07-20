from checks import unittest, verify_case

class TestV0315EventContractIntegrity(unittest.TestCase):
    def test_event_contract_integrity(self): verify_case(self, __name__.split(".")[-1])

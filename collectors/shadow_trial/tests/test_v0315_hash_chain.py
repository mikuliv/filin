from checks import unittest, verify_case

class TestV0315HashChain(unittest.TestCase):
    def test_hash_chain(self): verify_case(self, __name__.split(".")[-1])

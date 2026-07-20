from checks import unittest, verify_case

class TestV0315CausalSort(unittest.TestCase):
    def test_causal_sort(self): verify_case(self, __name__.split(".")[-1])

from checks import unittest, verify_case

class TestV0315AttackClassBalance(unittest.TestCase):
    def test_attack_class_balance(self): verify_case(self, __name__.split(".")[-1])

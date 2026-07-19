import unittest
from ml.tests.v0313_checks import check


class CheckV0313(unittest.TestCase):
    def test_attack_class_balance(self): check("attack_class_balance")


import unittest,numpy as np
from v037_support import *
from benign_ood_guard import BenignOODGuard
class TestOODGuard(unittest.TestCase):
 def test_ood_is_boolean_and_not_attack_label(self):
  x=np.arange(40,dtype=float).reshape(20,2);g=BenignOODGuard(.95).fit(x);self.assertEqual(g.is_ood(x).dtype,bool)

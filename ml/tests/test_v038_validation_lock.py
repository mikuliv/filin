import unittest
from v038_support import ROOT
class TestValidationLock(unittest.TestCase):
 def test_lock_requires_216(self):self.assertIn('len(combined) != 216',(ROOT/'ml/analysis/v038_validation_lock_audit.py').read_text(encoding='utf8'))

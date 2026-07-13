import unittest,tempfile
from pathlib import Path
from v037_support import *
from pipeline import sha256_file
class TestCandidateIntegrity(unittest.TestCase):
 def test_hash_changes_on_mutation(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'a';p.write_text('a');a=sha256_file(p);p.write_text('b');self.assertNotEqual(a,sha256_file(p))

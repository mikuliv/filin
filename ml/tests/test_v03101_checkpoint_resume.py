import tempfile,unittest
from pathlib import Path
from ml.performance.parallel_policy_evaluator import _read_checkpoint,_write_checkpoint,sha256
class TestCheckpoint(unittest.TestCase):
 def test_resume_and_mismatch(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/"x.json";r={"input_hash":"i","x":1};r["output_hash"]=sha256(r);_write_checkpoint(p,r)
   self.assertIsNotNone(_read_checkpoint(p,"i"));self.assertIsNone(_read_checkpoint(p,"wrong"))
 def test_partial_not_complete(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/"x.json";p.write_text('{"completed":false,"input_hash":"i"}');self.assertIsNone(_read_checkpoint(p,"i"))

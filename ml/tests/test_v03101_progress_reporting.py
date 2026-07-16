import tempfile,unittest,time
from pathlib import Path
from tools.performance.show_stage_progress import StageProgress
class TestProgress(unittest.TestCase):
 def test_eta(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/"p.json";r=StageProgress(10,p,time.monotonic()-2).update(5);self.assertEqual(r["percent"],50);self.assertIsNotNone(r["eta_seconds"]);self.assertTrue(p.exists())

from __future__ import annotations
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
class CaptureBarrierTests(unittest.TestCase):
 def test_runner_keeps_capture_after_last_execution(self):
  text=(ROOT/'lab'/'campaigns'/'run_v034_campaign.py').read_text(encoding='utf-8')
  self.assertIn('time.sleep(35)',text)

from __future__ import annotations
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
class AttemptArchiveTests(unittest.TestCase):
 def test_runner_archives_partial_artifacts_on_failure(self):
  text=(ROOT/'lab'/'campaigns'/'run_v034_campaign.py').read_text(encoding='utf-8')
  self.assertIn('failed_attempt',text);self.assertIn("attempt_{len(list(attempts.glob('attempt_*')))+1:03d}_failed",text)

from __future__ import annotations
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
class ResumeTests(unittest.TestCase):
 def test_resume_checks_verified_dataset(self):
  text=(ROOT/'lab'/'campaigns'/'run_v034_campaign.py').read_text(encoding='utf-8')
  self.assertIn('recovered_complete',text)
  self.assertIn('recovered_from_verified_dataset',text)

import hashlib, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
class CandidateIntegrityTests(unittest.TestCase):
 def test_frozen_candidate_hash_matches_manifest(self):
  import yaml
  m=yaml.safe_load((ROOT/'ml/experiments/v0_3_4/frozen_candidate_manifest.yaml').read_text())
  self.assertEqual(hashlib.sha256((ROOT/'ml/artifacts/v0_3_4/frozen_candidate.joblib').read_bytes()).hexdigest(),m['artifact_sha256'])

import unittest
from v038_episode_evidence import EpisodeEvidenceAccumulator
class TestOperationalDecision(unittest.TestCase):
 def test_novel_review(self):
  value=EpisodeEvidenceAccumulator().update(run_id='r',episode_id='e',raw_state='unsupported_novel',probabilities={'benign':.1},conformal_p_values={'benign':.1},support_set=set());self.assertEqual(value,'review_required:novel')

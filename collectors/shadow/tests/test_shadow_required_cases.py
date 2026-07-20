import copy,tempfile,unittest
from pathlib import Path
from collectors.shadow.canonical import canonical_bytes
from collectors.shadow.event_model import generate
from collectors.shadow.hash_chain import verify
from collectors.shadow.in_memory_sink import InMemorySink
from collectors.shadow.privacy import validate as privacy_validate
from collectors.shadow.queue import BoundedEventQueue
from collectors.shadow.schema_validator import validate
from collectors.shadow.spool import BoundedSpool,SpoolCorruption
import json,hashlib
ROOT=Path(__file__).resolve().parents[3]
def events():
 p=ROOT/'ml/reports/v0_3_13/immutable_prediction_manifest.json'; d=json.loads(p.read_text(encoding='utf-8')); return generate(d['records'][:20],'5ede6f9365a45766d0d89ef5b25e08f4fd1bfd7c5b47a0e47f300bba5aa750f7',hashlib.sha256(p.read_bytes()).hexdigest())
class RequiredCases(unittest.TestCase):
 def test_timestamp_not_in_canonical_identity(self):
  e=events()[0]; x=copy.deepcopy(e); x['event_created_at']='2099-01-01T00:00:00Z'; self.assertEqual(canonical_bytes(e,identity=True),canonical_bytes(x,identity=True))
 def test_forbidden_token_rejected(self):
  with self.assertRaises(ValueError): privacy_validate({'token':'fixture'})
 def test_raw_ip_rejected(self):
  with self.assertRaises(ValueError): privacy_validate({'message':'192.0.2.1'})
 def test_raw_feature_vector_rejected(self):
  with self.assertRaises(ValueError): privacy_validate({'feature_vector':[1]})
 def test_schema_missing_required_rejected(self):
  e=events()[0]; e.pop('event_id'); self.assertRaises(ValueError,validate,e)
 def test_sink_deduplicates(self):
  e=events()[0]; s=InMemorySink(); s.send(e); s.send(e); self.assertEqual((len(s.events),s.duplicates),(1,1))
 def test_modified_event_detected(self):
  rows=events(); rows[0]['primary_state']='modified'; self.assertFalse(verify(rows)['valid'])
 def test_missing_chain_link_detected(self):
  rows=events(); rows[1]['previous_event_hash']=None; self.assertFalse(verify(rows)['valid'])
 def test_queue_is_bounded(self):
  q=BoundedEventQueue(2); [q.put(e) for e in events()[:3]]; self.assertLessEqual(len(q),2); self.assertGreater(q.dropped,0)
 def test_alert_priority_wins(self):
  rows=events(); observation=next(e for e in rows if e['event_type']=='decision_observation'); alert=next((e for e in rows if e['event_type']=='alert_emitted'),None)
  if alert is None: self.skipTest('sample has no alert')
  q=BoundedEventQueue(1); q.put(observation); self.assertTrue(q.put(alert)); self.assertEqual(q.get()['event_type'],'alert_emitted')
 def test_spool_corruption_detected(self):
  with tempfile.TemporaryDirectory() as d:
   s=BoundedSpool(d); e=events()[0]; s.write(e); next(Path(d).glob('*.event')).write_text('{}',encoding='utf-8'); self.assertRaises(SpoolCorruption,s.recover)
 def test_event_id_is_deterministic(self): self.assertEqual([e['event_id'] for e in events()],[e['event_id'] for e in events()])
 def test_action_authority_absent(self): self.assertTrue(all(e['action_authority']=='none' and not e['enforcement_allowed'] for e in events()))

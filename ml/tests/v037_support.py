from __future__ import annotations
from pathlib import Path
import sys
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
for path in (ROOT,ROOT/'ml/features',ROOT/'ml/models',ROOT/'ml/decision',ROOT/'ml/experiments/v0_3_7',ROOT/'ml/analysis',ROOT/'lab/campaigns'):
 if str(path) not in sys.path:sys.path.insert(0,str(path))

from pipeline import ATTACK_CLASSES,DecisionParameters,decide_rows


def metric_rows():
 labels=['benign','benign']+ATTACK_CLASSES
 return pd.DataFrame({'run_id':['r']*len(labels),'episode_id':[f'e{i}' for i in range(len(labels))],
  'label':labels,'variant_id':['v']*len(labels),'environment_group':['g']*len(labels),
  'hard_negative_target_class':['low_rate_dos','',*['']*5]})


def perfect_predictions(rows=None):
 rows=metric_rows() if rows is None else rows;gate=np.array([.05 if x=='benign' else .95 for x in rows.label]);sub=np.zeros((len(rows),5))
 for i,label in enumerate(rows.label):sub[i,ATTACK_CLASSES.index(label) if label in ATTACK_CLASSES else 0]=1
 return decide_rows(rows,gate,sub,np.zeros(len(rows)),DecisionParameters(.2,.8,.55,1.0,'none'))


def raw_feature_row(run_id='r',flow=2,label='benign'):
 return {'run_id':run_id,'label':label,'flow_count':flow,'window_duration_seconds':2,'window_event_count':flow,
  'tcp_flow_count':flow,'udp_flow_count':0,'unique_destination_ip_count':1,'unique_destination_port_count':1,
  'orig_bytes_total':100,'resp_bytes_total':100,'total_bytes':200,'total_packets':4,
  'failed_connection_count':0,'successful_connection_count':flow,'http_request_count':1,'http_2xx_count':1}

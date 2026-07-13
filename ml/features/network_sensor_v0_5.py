"""Причинный stateful feature builder network_sensor_v0_5."""
from __future__ import annotations
from collections import deque
import hashlib,json
import numpy as np
import pandas as pd
from v034_profiles import RATE_FEATURES,project_row

TEMPORAL_FEATURES=[
'delta_flows_per_second','flows_per_second_to_rolling_median','robust_z_flows_per_second',
'delta_events_per_second','events_per_second_to_rolling_median','robust_z_events_per_second',
'delta_failed_connections_per_second','failed_connections_to_rolling_median','robust_z_failed_connections',
'delta_bytes_per_flow','bytes_per_flow_to_rolling_median','delta_packets_per_flow','packets_per_flow_to_rolling_median',
'delta_unique_destinations_per_flow','destination_set_jaccard_change','protocol_mix_l1_change',
'response_bytes_share_change','udp_flow_share_change','consecutive_high_failure_windows','consecutive_high_flow_windows',
'rolling_activity_slope','rolling_failure_slope','request_spacing_cv','periodicity_stability','long_lived_flow_persistence']
CONTEXT_FEATURES=['success_response_share','failed_then_successful_connection_rate','retry_recovery_rate','target_responsiveness_ratio','connection_completion_rate','long_lived_flow_share','http_method_diversity','http_response_status_entropy','response_direction_balance','service_availability_recovery_evidence']
CONTROL_FEATURES=list(RATE_FEATURES);TEMPORAL_ORDER=CONTROL_FEATURES+TEMPORAL_FEATURES;CONTEXTUAL_ORDER=TEMPORAL_ORDER+CONTEXT_FEATURES

def _safe_ratio(value,denominator):return float(value/max(abs(denominator),1e-9))
def _robust(value,history):
 if not history:return 0.0
 a=np.asarray(history,float);median=float(np.median(a));mad=float(np.median(np.abs(a-median)));return float((value-median)/max(1.4826*mad,1e-9))
def _slope(values):
 if len(values)<2:return 0.0
 return float(np.polyfit(np.arange(len(values)),np.asarray(values,float),1)[0])
class AssetState:
 def __init__(self,depth:int):self.depth=depth;self.history=deque(maxlen=depth);self.run_id=None
 def reset(self,run_id):self.history.clear();self.run_id=run_id
 def vector(self,row:dict,profile:str)->dict:
  if self.run_id!=row.get('run_id'):self.reset(row.get('run_id'))
  base=project_row(row,'network_sensor_v0_4_rates');previous=self.history[-1] if self.history else base
  def hist(name):return [x[name] for x in self.history]
  fps=base['flows_per_second'];eps=base['events_per_second'];fail=base['failed_connections_per_second'];bpf=base['bytes_per_flow'];ppf=base['packets_per_flow'];udp=base['udp_flow_share'];resp=base['response_bytes_share'];dest=base['unique_destinations_per_flow']
  temporal={
   'delta_flows_per_second':fps-previous['flows_per_second'],'flows_per_second_to_rolling_median':_safe_ratio(fps,np.median(hist('flows_per_second')) if self.history else fps),'robust_z_flows_per_second':_robust(fps,hist('flows_per_second')),
   'delta_events_per_second':eps-previous['events_per_second'],'events_per_second_to_rolling_median':_safe_ratio(eps,np.median(hist('events_per_second')) if self.history else eps),'robust_z_events_per_second':_robust(eps,hist('events_per_second')),
   'delta_failed_connections_per_second':fail-previous['failed_connections_per_second'],'failed_connections_to_rolling_median':_safe_ratio(fail,np.median(hist('failed_connections_per_second')) if self.history else fail),'robust_z_failed_connections':_robust(fail,hist('failed_connections_per_second')),
   'delta_bytes_per_flow':bpf-previous['bytes_per_flow'],'bytes_per_flow_to_rolling_median':_safe_ratio(bpf,np.median(hist('bytes_per_flow')) if self.history else bpf),'delta_packets_per_flow':ppf-previous['packets_per_flow'],'packets_per_flow_to_rolling_median':_safe_ratio(ppf,np.median(hist('packets_per_flow')) if self.history else ppf),
   'delta_unique_destinations_per_flow':dest-previous['unique_destinations_per_flow'],'destination_set_jaccard_change':min(1.0,abs(dest-previous['unique_destinations_per_flow'])),'protocol_mix_l1_change':abs(udp-previous['udp_flow_share'])+abs(base['tcp_flow_share']-previous['tcp_flow_share']),
   'response_bytes_share_change':resp-previous['response_bytes_share'],'udp_flow_share_change':udp-previous['udp_flow_share'],'consecutive_high_failure_windows':float(sum(x['failed_connection_rate']>.5 for x in self.history)+int(base['failed_connection_rate']>.5)),'consecutive_high_flow_windows':float(sum(x['flows_per_second']>np.median(hist('flows_per_second')) for x in self.history)+1 if self.history else 0),
   'rolling_activity_slope':_slope(hist('flows_per_second')+[fps]),'rolling_failure_slope':_slope(hist('failed_connections_per_second')+[fail]),'request_spacing_cv':float(row.get('flow_interarrival_std',0))/max(float(row.get('flow_interarrival_mean',0)),1e-9),'periodicity_stability':1.0-abs(float(row.get('flow_periodicity_score',0))-float(previous.get('_periodicity',row.get('flow_periodicity_score',0)))),'long_lived_flow_persistence':float(row.get('flow_duration_max',0)>1.0)+sum(x.get('_long',0) for x in self.history)}
  contextual={'success_response_share':float(row.get('http_2xx_count',0))/max(float(row.get('http_request_count',0)),1.0),'failed_then_successful_connection_rate':min(float(row.get('successful_connection_count',0)),float(row.get('failed_connection_count',0)))/max(float(row.get('flow_count',0)),1.0),'retry_recovery_rate':float(row.get('successful_connection_count',0))/max(float(row.get('failed_connection_count',0))+float(row.get('successful_connection_count',0)),1.0),'target_responsiveness_ratio':1.0-float(row.get('http_error_rate',0)),'connection_completion_rate':float(row.get('connection_success_rate',0)),'long_lived_flow_share':float(row.get('flow_duration_max',0)>1.0)/max(float(row.get('flow_count',0)),1.0),'http_method_diversity':float((row.get('http_get_count',0)>0)+(row.get('http_post_count',0)>0))/2.0,'http_response_status_entropy':float((row.get('http_2xx_count',0)>0)+(row.get('http_4xx_count',0)>0)+(row.get('http_5xx_count',0)>0))/3.0,'response_direction_balance':1.0-abs(0.5-resp)*2,'service_availability_recovery_evidence':float(row.get('successful_connection_count',0)>0 and row.get('failed_connection_count',0)>0)}
  state={**base,'_periodicity':float(row.get('flow_periodicity_score',0)),'_long':float(row.get('flow_duration_max',0)>1.0)};self.history.append(state)
  if profile=='network_sensor_v0_4_rates_control':return base
  if profile=='network_sensor_v0_5_temporal':return {**base,**temporal}
  if profile=='network_sensor_v0_5_contextual':return {**base,**temporal,**contextual}
  raise KeyError(profile)
def build_causal_frame(rows,profile,history_depth=4):
 state=AssetState(history_depth);vectors=[]
 for row in rows:vectors.append(state.vector(dict(row),profile))
 order={'network_sensor_v0_4_rates_control':CONTROL_FEATURES,'network_sensor_v0_5_temporal':TEMPORAL_ORDER,'network_sensor_v0_5_contextual':CONTEXTUAL_ORDER}[profile]
 return pd.DataFrame(vectors,columns=order)
def schema_sha(profile):
 order={'network_sensor_v0_4_rates_control':CONTROL_FEATURES,'network_sensor_v0_5_temporal':TEMPORAL_ORDER,'network_sensor_v0_5_contextual':CONTEXTUAL_ORDER}[profile]
 return hashlib.sha256(json.dumps(order,separators=(',',':')).encode()).hexdigest()

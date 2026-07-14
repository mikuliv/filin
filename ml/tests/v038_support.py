from __future__ import annotations
import sys
import importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
for path in (ROOT,ROOT/'ml/features',ROOT/'ml/models',ROOT/'ml/decision',ROOT/'ml/experiments/v0_3_8',ROOT/'ml/analysis',ROOT/'lab/campaigns'):
 if str(path) not in sys.path:sys.path.insert(0,str(path))

def load_v038(name,relative):
 spec=importlib.util.spec_from_file_location(name,ROOT/relative);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def raw_row(run_id='r',label='benign',flow=2):
 return {'run_id':run_id,'label':label,'flow_count':flow,'window_duration_seconds':2,'window_event_count':flow,
 'tcp_flow_count':flow,'udp_flow_count':0,'unique_destination_ip_count':1,'unique_destination_port_count':1,'unique_service_count':1,
 'orig_bytes_total':100,'resp_bytes_total':100,'total_bytes':200,'orig_packets_total':2,'resp_packets_total':2,'total_packets':4,
 'failed_connection_count':0,'successful_connection_count':flow,'connection_success_rate':1,'connection_failure_rate':0,
 'http_request_count':1,'http_get_count':1,'http_post_count':0,'http_2xx_count':1,'http_4xx_count':0,'http_5xx_count':0,'http_error_rate':0,
 'dns_query_count':0,'dns_error_rate':0,'flow_interarrival_mean':1,'flow_interarrival_std':0,'flow_periodicity_score':0,'flow_burst_score':0,'flow_duration_max':1}

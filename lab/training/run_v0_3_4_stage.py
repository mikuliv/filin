"""Guarded v0.3.4 stage entry point."""
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'ml'/'training'),str(ROOT/'lab'/'campaigns')]
from v034_campaign import load_campaign
from v034_data_access import assert_allowed_campaign,load_policy,policy_sha256
def main() -> None:
 p=argparse.ArgumentParser();p.add_argument('--training-campaign',required=True);p.add_argument('--validation-campaign',required=True);p.add_argument('--data-access-policy',required=True);p.add_argument('--strict',action='store_true');p.add_argument('--resume',action='store_true');a=p.parse_args()
 policy=load_policy(Path(a.data_access_policy));train=load_campaign(Path(a.training_campaign));valid=load_campaign(Path(a.validation_campaign))
 assert_allowed_campaign(train['campaign_id'],'training',policy);assert_allowed_campaign(valid['campaign_id'],'validation',policy)
 print(json.dumps({'v034_data_access_valid':True,'data_access_policy_sha256':policy_sha256(Path(a.data_access_policy)),'training_runs_planned':len(train['runs']),'validation_runs_planned':len(valid['runs']),'v033_feature_rows_loaded':False,'status':'preflight_only_no_campaign_execution'},ensure_ascii=False,indent=2))
if __name__=='__main__': main()

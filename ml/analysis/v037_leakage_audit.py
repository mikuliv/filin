FORBIDDEN={'run_id','execution_id','episode_id','episode_position','label','binary_label','scenario_id','scenario_execution_key','variant_id','group','workflow_profile','hard_negative_target_class','seed','warmup','raw_ip','hashed_ip','hostname','raw_uri','port_identifier','container_name','zeek_uid','campaign_id','dataset_path','artifact_hash'}
def audit(columns):
 found=sorted(set(columns)&FORBIDDEN);return {'v037_leakage_valid':not found,'forbidden_features':found,'future_values':False,'identity_exposed':False}

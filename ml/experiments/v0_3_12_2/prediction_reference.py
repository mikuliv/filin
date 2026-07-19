from __future__ import annotations
from .common import sha256_file,write_json
def create(source_stage,source_lock,source_prediction,row_count,episode_count,output):
    payload={"source_stage":"v0.3.12","benchmark_source_stage":source_stage,"source_input_lock_sha256":source_lock["input_lock_sha256"],"source_prediction_sha256":sha256_file(source_prediction),"row_count":row_count,"episode_count":episode_count,"new_prediction_generated":False,"reference_manifest_created_post_hoc":True,"scientific_basis":"integrity_v0.3.12_and_v0.3.12.1"}; write_json(output,payload); return payload

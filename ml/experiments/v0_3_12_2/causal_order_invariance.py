from __future__ import annotations
import random
from .common import sha256_json
def variants(records):
    out={"canonical":list(records),"reverse":list(reversed(records))}
    for seed in (101,202,303):
        rows=list(records); random.Random(seed).shuffle(rows); out[f"shuffle_{seed}"]=rows
    blocks={}
    for row in records: blocks.setdefault((row["run_id"],row["activity_key"]),[]).append(row)
    keys=list(blocks); random.Random(404).shuffle(keys); out["group_block_shuffle"]=[r for k in keys for r in blocks[k]]
    return out
def audit(records,evaluator):
    outputs={name:evaluator(rows) for name,rows in variants(records).items()}; hashes={name:sha256_json(value) for name,value in outputs.items()}; reference=hashes["canonical"]
    return {"causal_order_invariance_passed":all(v==reference for v in hashes.values()),"shuffle_profile_count":len(outputs)-1,"profile_count":len(outputs),"canonical_result_sha256":reference,"profile_hashes":hashes,"exact_equivalence":all(v==reference for v in hashes.values()),"float_tolerance":1e-12}

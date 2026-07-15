from __future__ import annotations
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/"ml/decision"),str(ROOT/"ml/experiments/v0_3_10"),str(ROOT/"ml/analysis"),str(ROOT/"ml/features"),str(ROOT/"lab/campaigns")]
from v0310_minimal_promotion import ATTACK_CLASSES,CLASSES,MinimalPromotionDecision,MinimalPromotionPolicy

def policy(**changes):
    values=dict(strong_thresholds_per_class={label:.8 for label in ATTACK_CLASSES},strong_probability_margin=.2,
      maximum_strong_benign_probability=.2,weak_thresholds_per_class={label:.45 for label in ATTACK_CLASSES},
      weak_probability_margin=0.0,weak_benign_ceiling=.5,weak_repetition_policy="two_of_three",pending_ttl_windows=3,
      ambiguity_margin=.07,strong_benign_probability=.8,strong_benign_margin=.3,dedup_ttl_windows=3)
    values.update(changes);return MinimalPromotionPolicy(**values)

def probabilities(top="port_scan",value=.9,benign=.05):
    result={label:.01 for label in CLASSES};result["benign"]=benign;result[top]=value
    remainder=1-sum(result.values());result["auth_failures" if top!="auth_failures" else "web_probe"]+=remainder
    return result

def engine(**changes):return MinimalPromotionDecision(policy(**changes))

"""Post-hoc OOD-анализ frozen candidate v0.3.7 без изменения threshold."""
from __future__ import annotations
import pandas as pd


def analyze(rows: pd.DataFrame, predictions: pd.DataFrame, frozen_threshold: float) -> dict:
    extra=predictions[[column for column in predictions.columns if column not in rows.columns]]
    frame=pd.concat([rows.reset_index(drop=True),extra.reset_index(drop=True)],axis=1)
    def rate(part):return float(part['is_ood'].mean()) if len(part) else 0.0
    return {
        'frozen_threshold':float(frozen_threshold),'threshold_changed_on_validation':False,
        'ood_rate_overall':rate(frame),'ood_rate_benign':rate(frame[frame.label=='benign']),
        'ood_rate_attack':rate(frame[frame.label!='benign']),
        'ood_rate_per_group':{str(k):rate(v) for k,v in frame.groupby('environment_group')},
        'ood_rate_per_benign_variant':{str(k):rate(v) for k,v in frame[frame.label=='benign'].groupby('variant_id')},
        'ood_rate_per_attack_class':{str(k):rate(v) for k,v in frame[frame.label!='benign'].groupby('label')},
        'ood_automatically_mapped_to_attack':False,
        'ood_masks_majority_of_attacks':bool(rate(frame[frame.label!='benign'])>.5),
    }

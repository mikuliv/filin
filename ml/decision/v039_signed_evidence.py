"""Причинное signed accumulation по attack-классам."""
from __future__ import annotations

from v039_evidence_record import ATTACK_CLASSES


class SignedClassEvidence:
    def __init__(self, decay: float, activation_threshold: float):
        self.decay=float(decay); self.activation_threshold=float(activation_threshold); self.scores={name:0.0 for name in ATTACK_CLASSES}

    @staticmethod
    def _component(record: dict, label: str) -> float:
        probabilities=record["joint_probabilities"]; cset=set(record["conformal_set"])
        conformal=1.0 if len(cset)==1 and label in cset else (0.5 if label in cset else 0.0)
        others=max(value for name,value in probabilities.items() if name != label)
        probability_margin=max(0.0, probabilities[label]-others)
        support_margin=max(0.0, record["support_margins"][label])
        return .50*probabilities[label]+.20*conformal+.15*probability_margin+.15*min(support_margin,1.0)

    def update(self, record: dict) -> dict[str,float]:
        benign=self._component(record,"benign")
        for label in ATTACK_CLASSES:
            self.scores[label]=max(0.0,self.decay*self.scores[label]+self._component(record,label)-benign)
        return dict(self.scores)

    def reset(self):
        self.scores={name:0.0 for name in ATTACK_CLASSES}

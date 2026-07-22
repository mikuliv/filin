from __future__ import annotations

import numpy as np
from scipy.special import expit, logit
from sklearn.linear_model import LogisticRegression


CLASSES = ["benign", "auth_failures", "beacon", "low_rate_dos", "port_scan", "web_probe"]
ATTACKS = CLASSES[1:]


class BinarySigmoidCalibrator:
    def fit(self, probabilities, labels):
        x = logit(np.clip(np.asarray(probabilities), 1e-7, 1 - 1e-7)).reshape(-1, 1)
        self.model = LogisticRegression(random_state=3154).fit(x, labels)
        return self

    def predict(self, probabilities):
        x = logit(np.clip(np.asarray(probabilities), 1e-7, 1 - 1e-7)).reshape(-1, 1)
        return self.model.predict_proba(x)[:, 1]


class SubtypeSigmoidCalibrator:
    def fit(self, probabilities, labels):
        p = np.clip(np.asarray(probabilities), 1e-7, 1 - 1e-7)
        self.models = []
        for index in range(p.shape[1]):
            model = LogisticRegression(random_state=3154 + index).fit(logit(p[:, index]).reshape(-1, 1), np.asarray(labels) == index)
            self.models.append(model)
        return self

    def predict(self, probabilities):
        p = np.clip(np.asarray(probabilities), 1e-7, 1 - 1e-7)
        calibrated = np.column_stack([model.predict_proba(logit(p[:, i]).reshape(-1, 1))[:, 1] for i, model in enumerate(self.models)])
        return calibrated / calibrated.sum(axis=1, keepdims=True)


def aligned(model, x, classes):
    source = model.predict_proba(x)
    result = np.zeros((len(x), len(classes)))
    for position, value in enumerate(model.classes_):
        result[:, classes.index(value)] = source[:, position]
    return result


def joint_probabilities(bundle, x):
    gate_raw = aligned(bundle["gate"], x, [0, 1])[:, 1]
    subtype_raw = aligned(bundle["subtype"], x, ATTACKS)
    gate = bundle["gate_calibrator"].predict(gate_raw)
    subtype = bundle["subtype_calibrator"].predict(subtype_raw)
    return np.column_stack([1 - gate, gate[:, None] * subtype]), gate, subtype


def conformal_sets(bundle, probabilities):
    thresholds = bundle["conformal_thresholds"]
    return [[name for name, probability in zip(CLASSES, row) if probability >= thresholds[name]] for row in probabilities]

from __future__ import annotations


class BlindLabelGuard:
    def __init__(self):
        self.prediction_sha256 = None
        self.label_read_count = 0

    def freeze_prediction(self, prediction_sha256: str):
        if not prediction_sha256:
            raise RuntimeError("Нельзя открыть labels без immutable prediction hash")
        self.prediction_sha256 = prediction_sha256

    def unlock(self, loader):
        if self.prediction_sha256 is None:
            self.label_read_count += 1
            raise PermissionError("Label vault закрыт до immutable prediction freeze")
        self.label_read_count += 1
        return loader()

    def report(self):
        return {"prediction_phase_label_read_count": max(self.label_read_count - (1 if self.prediction_sha256 else 0), 0), "label_vault_unlocked_after_prediction": self.prediction_sha256 is not None, "blind_label_separation_passed": self.prediction_sha256 is not None}

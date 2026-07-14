import json
import tempfile
import unittest
from pathlib import Path

from ml.evaluation.predict_only import RuntimeNoFitGuard, audit_entrypoint, run_predict_only


class DummyEstimator:
    def __init__(self):
        self.predict_calls = 0

    def fit(self, values):
        return self

    def fit_transform(self, values):
        return values

    def partial_fit(self, values):
        return self

    def calibrate(self):
        return self

    def tune(self):
        return self

    def predict(self, values):
        self.predict_calls += 1
        return [1 for _ in values]


class SelfFittingEstimator(DummyEstimator):
    def predict(self, values):
        self.fit(values)
        return super().predict(values)


class TestFuturePredictOnlyGuard(unittest.TestCase):
    def test_real_estimator_training_methods_are_blocked(self):
        estimator = DummyEstimator()
        guard = RuntimeNoFitGuard(estimator)
        with guard:
            for name in ("fit", "fit_transform", "partial_fit", "calibrate", "tune"):
                with self.assertRaises(RuntimeError):
                    getattr(estimator, name)([])
            self.assertEqual(estimator.predict([[1]]), [1])
        self.assertEqual(guard.audit()["fit_call_count"], 1)

    def test_guard_blocks_fit_called_from_inside_predict(self):
        with RuntimeNoFitGuard(SelfFittingEstimator()) as guard:
            with self.assertRaises(RuntimeError):
                guard.artifact.predict([[1]])

    def test_prediction_hash_and_resume_without_second_inference(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            artifact = root / "model.bin"
            artifact.write_bytes(b"immutable-model")
            output = root / "output"
            estimator = DummyEstimator()
            result = run_predict_only(artifact, [[1], [2]], output, loader=lambda _: estimator)
            self.assertEqual(result["status"], "completed")
            self.assertEqual(estimator.predict_calls, 1)
            resumed = run_predict_only(
                artifact, [[9]], output, resume=True,
                loader=lambda _: self.fail("resume must not load the model"),
            )
            self.assertEqual(resumed["status"], "resumed")
            self.assertFalse(resumed["prediction_performed"])
            self.assertEqual(estimator.predict_calls, 1)

    def test_tampered_predictions_block_resume(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            artifact = root / "model.bin"
            artifact.write_bytes(b"immutable-model")
            output = root / "output"
            run_predict_only(artifact, [[1]], output, loader=lambda _: DummyEstimator())
            (output / "predictions.json").write_text("[]", encoding="utf-8")
            with self.assertRaises(RuntimeError):
                run_predict_only(artifact, [], output, resume=True)

    def test_entrypoint_does_not_import_training_modules(self):
        source = Path(__file__).parents[1] / "evaluation" / "predict_only.py"
        result = audit_entrypoint(source)
        self.assertEqual(result["status"], "passed")
        self.assertFalse(result["training_modules_imported"])


if __name__ == "__main__":
    unittest.main()

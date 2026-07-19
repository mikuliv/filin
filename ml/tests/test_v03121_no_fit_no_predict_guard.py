import unittest
from ml.tests._v03121_support import V03121Mixin,load,ROOT,REPORT,yaml
from ml.audits.v0_3_12_1.no_fit_no_predict_guard import NoFitNoPredictGuard
from sklearn.ensemble import HistGradientBoostingClassifier

class V03121NoFitNoPredictGuard(V03121Mixin,unittest.TestCase):
    def test_requirement(self): self.assert_result_flag('no_fit_no_predict_audit_passed')
    def test_fit_is_blocked(self):
        with NoFitNoPredictGuard() as guard:
            with self.assertRaises(RuntimeError): HistGradientBoostingClassifier().fit([[0],[1]],[0,1])
        self.assertEqual(guard.report()["fit_call_count"],1)
    def test_predict_is_blocked(self):
        with NoFitNoPredictGuard() as guard:
            with self.assertRaises(RuntimeError): HistGradientBoostingClassifier().predict([[0]])
        self.assertEqual(guard.report()["prediction_generation_count"],1)

# Аудит v0.3.12.1

Технический post-hoc аудит объясняет задержку alert emission, дискретность frozen gate и покрытие исторических regression-наборов. Он читает только immutable predictions v0.3.9/v0.3.10 и frozen mappings; обучение, prediction, tuning, повторная feature extraction и изменение статуса v0.3.12 запрещены.

```powershell
python ml/audits/v0_3_12_1/run_v0_3_12_1_audit.py --protocol ml/audits/v0_3_12_1/audit_protocol.yaml --source-result ml/experiments/v0_3_12/frozen_regression_result.yaml --source-doc docs/experiments/v0_3_12.md --workers auto --strict --resume
```

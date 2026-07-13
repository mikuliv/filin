# Holdout v0.3.6

Каталог содержит protocol-aware preflight, профили условий, safety policy и идемпотентный stage runner.
Collection не импортирует `joblib` и не загружает frozen candidate. Модель разрешено открыть только после
создания `holdout_lock_manifest.yaml`. `--resume` использует уже заблокированные predictions и не вызывает
повторный predict.

```powershell
python lab/holdout/run_v0_3_6_stage.py --campaign lab/campaigns/v0_3_6_blind_holdout.yaml --protocol ml/experiments/v0_3_6/holdout_protocol.yaml --policy ml/experiments/v0_3_6/holdout_evaluation_policy.yaml --candidate-manifest ml/experiments/v0_3_4/frozen_candidate_manifest.yaml --output-root lab/output --report-dir ml/reports/v0_3_6 --artifact-dir ml/artifacts/v0_3_6 --strict --resume
```

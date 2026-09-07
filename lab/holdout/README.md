# Отложенная контрольная выборка v0.3.6

Каталог содержит безопасный этап слепой проверки кандидата на отложенной контрольной выборке.

Каталог содержит проверку протокола, профили условий, политику безопасности и идемпотентный модуль запуска.
Набор не импортирует `joblib` и не загружает зафиксированный кандидат. Модель разрешено открыть только после
создания `holdout_lock_manifest.yaml`. `--resume` использует уже заблокированные прогнозы и не вызывает
повторное предсказание.

```powershell
python lab/holdout/run_v0_3_6_stage.py --campaign lab/campaigns/v0_3_6_blind_holdout.yaml --protocol ml/experiments/v0_3_6/holdout_protocol.yaml --policy ml/experiments/v0_3_6/holdout_evaluation_policy.yaml --candidate-manifest ml/experiments/v0_3_4/frozen_candidate_manifest.yaml --output-root lab/output --report-dir ml/reports/v0_3_6 --artifact-dir ml/artifacts/v0_3_6 --strict --resume
```

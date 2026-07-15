# Филин v0.3.10 — minimal probability-conformal promotion

Новый независимый training/internal-validation cycle проверяет, был ли низкий episode recall v0.3.9 следствием сложного decision layer. Строки и predictions v0.3.6–v0.3.9 запрещены fail-closed политикой; старые агрегированные выводы используются только как заранее зафиксированное архитектурное основание.

Base HGB/HGB, 51 causal contextual features, group-aware OOF sigmoid и Mondrian `alpha=0.05` сохранены. Continuous class support рассчитывается только диагностически. Основной candidate использует два пути: strong singleton может создать alert по первому окну, а умеренное evidence требует двух согласованных окон. Pending не является benign, review или alert.

Alert представлен однократным immutable emission event. Deduplication с TTL три scored windows подавляет повтор события, но не удерживает active state и не меняет уже установленный episode detection.

Полный запуск:

```powershell
python ml/experiments/v0_3_10/run_v0_3_10_stage.py `
  --training-campaign lab/campaigns/v0_3_10_training.yaml `
  --validation-campaign lab/campaigns/v0_3_10_internal_validation.yaml `
  --protocol ml/experiments/v0_3_10/protocol.yaml `
  --data-policy ml/experiments/v0_3_10/data_access_policy.yaml `
  --selection-policy ml/experiments/v0_3_10/model_selection_policy.yaml `
  --validation-policy ml/experiments/v0_3_10/internal_validation_policy.yaml `
  --output-root lab/output --report-dir ml/reports/v0_3_10 `
  --artifact-dir ml/artifacts/v0_3_10 --strict --resume
```

Validation prediction блокируется, пока pre-prediction lock не содержит все 360 canonical `captures/` hashes. Post-hoc дополнение capture evidence запрещено.

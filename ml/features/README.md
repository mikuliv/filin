# Признаки модели

## Назначение и статус

Текущий версионированный признак layer; основной contract — `network_features_v2`.

## Место в архитектуре

Преобразует normalized observations во вход Зафиксировано candidate.

## Входы и выходы

Разрешены только fields, доступные к decision time. Output содержит стабильный
порядок 51 features, типы и preprocessing identity.

## Границы и запреты

Post-outcome leakage, silent reorder и подмена contract запрещены.

## Безопасный запуск и тестирование

```powershell
python -m pytest ml/tests -q -k feature
```

## Источники истины

признак manifests, candidate манифест и [causal features](../../docs/research/causal-features.md).

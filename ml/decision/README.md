# Политика решения

## Назначение и статус

Текущий frozen inference/episode/state layer для candidate `v03154`.

## Место в архитектуре

Преобразует model scores и conformal output в passive episode decision.

## Входы и выходы

Входы закреплены candidate manifest; выход формирует class/abstention state для
`shadow_event_v2`.

## Границы и запреты

Forced winner, runtime threshold tuning и automatic enforcement запрещены.

## Безопасный запуск и тестирование

```powershell
python -m pytest ml/tests -q -k decision
```

## Источники истины

Candidate manifest, state policy artifacts и [uncertainty guide](../../docs/research/uncertainty-and-abstention.md).

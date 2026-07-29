# Политика решения

## Назначение и статус

Текущий зафиксированное применение модели/episode/state layer для candidate `v03154`.

## Место в архитектуре

Преобразует модель scores и conformal output в passive episode decision.

## Входы и выходы

Входы закреплены candidate манифест; выход формирует class/abstention state для
контракт пассивного события (`shadow_event_v2`).

## Границы и запреты

принудительный выбор победителя, среда выполнения threshold tuning и automatic enforcement запрещены.

## Безопасный запуск и тестирование

```powershell
python -m pytest ml/tests -q -k decision
```

## Источники истины

Candidate манифест, state policy artifacts и [uncertainty guide](../../docs/research/uncertainty-and-abstention.md).

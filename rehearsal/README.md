# Контролируемая локальная репетиция

## Назначение

Воспроизводимая локальная проверка transport, timing, recovery и evidence collection.

## Статус

`current laboratory tool`; не external trial.

## Место в архитектуре

Проверяет staging path основной линии в изолированной среде.

## Основные каталоги

Contracts, runner components и local fixtures находятся в `rehearsal/`.

## Разрешённые входы и выходы

Frozen synthetic scenarios; outputs пишутся в runtime и stage reports по protocol.

## Границы и запреты

Запрещены real notifications, external endpoints и трактовка результата как production readiness.

## Безопасный запуск

Только команда конкретного frozen protocol; общий quick runner намеренно не публикуется.

## Тестирование

```powershell
python -m pytest ml/tests/test_v0317_rehearsal.py -q
```

## Источники истины

`rehearsal/contracts/`, protocols `v0.3.17*` и их policy results.

# Контролируемая локальная репетиция

## Назначение

Воспроизводимая локальная проверка transport, timing, восстановление и подтверждающие материалы collection.

## Статус

`current laboratory tool`; не external trial.

## Место в архитектуре

Проверяет staging path основной линии в изолированной среде.

## Основные каталоги

Contracts, модуль запуска components и local fixtures находятся в `rehearsal/`.

## Разрешённые входы и выходы

Зафиксировано synthetic scenarios; outputs пишутся в среда выполнения и stage reports по protocol.

## Границы и запреты

Запрещены real notifications, external endpoints и трактовка результата как промышленная эксплуатация readiness.

## Безопасный запуск

Только команда конкретного Зафиксировано protocol; общий quick модуль запуска намеренно не публикуется.

## Тестирование

```powershell
python -m pytest ml/tests/test_v0317_rehearsal.py -q
```

## Источники истины

`rehearsal/contracts/`, protocols `v0.3.17*` и их policy results.

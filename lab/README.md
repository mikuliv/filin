# Лабораторная среда

## Назначение

Изолированные scenarios, environments, sensors, campaigns, holdouts и robustness checks.

## Статус

`experimental` и `laboratory-only`.

## Место в архитектуре

Среда создаёт контролируемые inputs основной линии и не является внешней площадкой.

## Основные каталоги

`environment/`, `sensor/`, `campaigns/`, `holdout/`, `robustness/`, `training/`, `docker/`.

## Разрешённые входы и выходы

Только synthetic сценарии и локальные fixtures. Outputs пишутся в разрешённый runtime.

## Границы и запреты

Запрещены выход из изоляции, production traffic и трактовка rehearsal как external trial.

## Безопасный запуск

Запускайте только command, указанный frozen protocol конкретного stage.

## Тестирование

```powershell
python -m pytest ml/tests -q
```

## Источники истины

Frozen protocols, policy results и [research methodology](../docs/research/methodology.md).

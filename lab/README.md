# Лабораторная среда

## Назначение

Изолированные scenarios, environments, sensors, Кампании, holdouts и robustness checks.

## Статус

`experimental` и `laboratory-only`.

## Место в архитектуре

Среда создаёт контролируемые inputs основной линии и не является внешней площадкой.

## Основные каталоги

`environment/`, `sensor/`, `campaigns/`, `holdout/`, `robustness/`, `training/`,
`docker/`, `network_validation/`.

`network_validation/` содержит технический каркас будущей независимой сетевой
проверки: общий Docker-клиент, две реализации генераторов, два target-профиля,
capture sidecar, строгие контракты и dry-run CLI. Эксперимент этим изменением не
запущен; подробности приведены в [локальном README](network_validation/README.md).

## Разрешённые входы и выходы

Только synthetic сценарии и локальные fixtures. Outputs пишутся в разрешённый среда выполнения.

## Границы и запреты

Запрещены выход из изоляции, промышленная эксплуатация traffic и трактовка rehearsal как external trial.

## Безопасный запуск

Запускайте только command, указанный Зафиксировано protocol конкретного stage.

## Тестирование

```powershell
python -m pytest ml/tests -q
```

## Источники истины

Зафиксировано protocols, policy results и [research methodology](../docs/research/methodology.md).

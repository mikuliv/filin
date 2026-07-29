# Сборщики

## Назначение

Сбор и нормализация CSV, Zeek и Suricata observations, а также passive shadow среда выполнения.

## Статус

`current`, laboratory-scoped.

## Место в архитектуре

Компонент формирует вход признак pipeline и `shadow_event_v2` основной линии.

## Основные каталоги

`csv_collector/`, `zeek_collector/`, `suricata_collector/`, `shadow/` и `shadow_trial/`.

## Разрешённые входы

Контролируемые fixtures и formats, предусмотренные версионированный contracts.

## Выходы

Нормализованные records, признак inputs и passive events с candidate identity.

## Границы и запреты

промышленная эксплуатация capture, скрытая отправка наружу и неизвестный candidate запрещены.

## Безопасный запуск и тестирование

```powershell
python -m pytest collectors -q
```

## Источники истины

`collectors/shadow/contracts/candidate_registry_v1.json`, collector schemas и
[detection/среда выполнения architecture](../docs/architecture/detection-and-runtime-track.md).

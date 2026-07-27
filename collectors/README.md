# Collectors

## Назначение

Сбор и нормализация CSV, Zeek и Suricata observations, а также passive shadow runtime.

## Статус

`current`, laboratory-scoped.

## Место в архитектуре

Компонент формирует вход feature pipeline и `shadow_event_v2` основной линии.

## Основные каталоги

`csv_collector/`, `zeek_collector/`, `suricata_collector/`, `shadow/` и `shadow_trial/`.

## Разрешённые входы

Контролируемые fixtures и formats, предусмотренные versioned contracts.

## Выходы

Нормализованные records, feature inputs и passive events с candidate identity.

## Границы и запреты

Production capture, скрытая отправка наружу и неизвестный candidate запрещены.

## Безопасный запуск и тестирование

```powershell
python -m pytest collectors -q
```

## Источники истины

`collectors/shadow/contracts/candidate_registry_v1.json`, collector schemas и
[detection/runtime architecture](../docs/architecture/detection-and-runtime-track.md).

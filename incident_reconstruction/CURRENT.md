# Incident reconstruction: текущий обзор v0.4.0–v0.4.4

## Почему отдельный файл

`incident_reconstruction/README.md` входит во Зафиксировано комплект и не может быть изменён.
Этот документ является современной редакцией без подмены защищённых байтов.

## Назначение и статус

Текущая laboratory subsystem преобразует passive event и подтверждающие материалы references в
facts, temporal/structural relations, разрывы, correlation groups, competing гипотезы
и incident card v2. Этапы `v0.4.0–v0.4.4` завершены; external applicability не подтверждена.

## Место в архитектуре

Вход расположен после `shadow_event_v2`, выход потребляет `lab_console/`.

## Основные каталоги

`contracts/`, `protocols/`, builders, validators, scenarios и tests.

## Разрешённые входы и выходы

Только версионированный laboratory bundles. Outputs — deterministic cards и explanation views.

## Границы и запреты

Fact требует подтверждающие материалы; temporal/graph relation не доказывает причинность; hypothesis
не является фактом; принудительный выбор победителя и automatic response запрещены.

## Безопасный запуск и тестирование

```powershell
python -m pytest ml/tests/test_v040_incident_reconstruction.py ml/tests/test_v041_temporal_reconstruction.py ml/tests/test_v042_hypothesis_analysis.py -q
```

## Источники истины

версионированный schemas, Зафиксировано protocols, v0.4 policy results и
[архитектурный обзор](../docs/architecture/reconstruction-and-analysis-track.md).

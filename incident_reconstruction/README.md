# Проверяемая реконструкция инцидента v0.4.0

Модуль принимает только готовые пассивные события `shadow_event_v2`. Он не
загружает модель, не меняет результат классификации и не обращается к backend.

## Поток данных

```text
пассивное событие → подтверждающий материал → наблюдаемый факт
→ временная последовательность → гипотеза → карточка инцидента
```

Факт копирует только разрешённые поля источника. Гипотеза всегда отделена от
фактов, содержит недостающие сведения и альтернативное объяснение. Одинаковый
канонический вход создаёт побайтно одинаковую смысловую карточку.

## Команды

```powershell
python -m incident_reconstruction.cli build-card --events events.json --run-id v040_example_001 --output card.json
python -m incident_reconstruction.cli validate-card --card card.json --events events.json
python -m incident_reconstruction.cli build-bundle --events events.json --run-id v040_example_001 --output bundle.json
python tools/incident_reconstruction/verify_bundle.py --bundle bundle.json
```

## Границы

Карточка создаётся на синтетических лабораторных данных, не подтверждает
компрометацию и предназначена только для анализа специалистом. Рекомендации
не выполняются автоматически.

## Связанные документы

- [Описание этапа](../docs/experiments/v0_4_0.md)
- [Архитектура и ограничения](../docs/research/incident-reconstruction.md)
- [Состояние параллельной линии](../docs/status/v0_4_track.yaml)
- [Frozen protocol](protocols/v0_4_0_protocol_r1.yaml)

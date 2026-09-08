# Сетевой сенсор Zeek

Сенсор — независимый наблюдатель фактического трафика. Он не получает метку класса,
не читает сценарий и не создаёт сетевые события из клиентского CSV; единственным
первичным источником является захваченный PCAP.

## Назначение

Независимое наблюдение фактически захваченного трафика Docker и его преобразование в `network_sensor_v0_3`.

## Что реализовано

Capture-sidecar пассивно наблюдает namespace `traffic-client`; PCAP хранится в Docker named volume. Offline Zeek создаёт logs, parser и normalizer формируют sensor events, а markers задают интервалы корреляции.

## Основные файлы

- `capture_preflight.py` — проверка захвата и протокола маркера;
- `zeek_log_parser.py`, `normalize_zeek_events.py` — обработка Zeek logs;
- `correlate_sensor_events.py` — marker-aware correlation;
- `run_v0_3_sensor_stage.py` — stage модуль запуска.

## Входные данные и выходные данные

Первичный источник — PCAP. События Zeek не создаются из `traffic_events.jsonl`, клиентского CSV или меток. Выходные журналы, события и CSV — артефакты среды выполнения.

## Запуск

`python lab/sensor/run_v0_3_sensor_stage.py --help`

## Проверки

Markers реально проходят сеть, но исключаются из aggregation. Correlation не использует labels и не расширяет tolerance до минут.

## Ограничения

Наблюдаемость определяется топологией и видимостью Zeek logs.

## Связанные документы

[Архитектура](../../docs/architecture.md), [происхождение](../../docs/data-provenance.md), [ограничения](../../docs/limitations.md).

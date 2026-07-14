# Лабораторный стенд

## Prospective holdout v0.3.6

`holdout/` отделяет collection/lock от one-time evaluation. Candidate artifact не загружается до
holdout lock; backend не изменяется.

## Назначение

Изолированное воспроизводимое выполнение безопасных Docker-сценариев и получение фактических client/sensor observations.

## Что реализовано

Стенд запускает независимые runs, фиксирует execution metadata, создаёт start/end markers, пассивно захватывает трафик и передаёт PCAP в offline Zeek processing.

## Основные файлы

- `campaigns/` — campaign manifests и runners;
- `sensor/` — capture, Zeek, markers и корреляция;
- `tools/` — вспомогательные laboratory scripts.

## Входные и выходные данные

Manifests и безопасные сценарии являются входом. PCAP, Zeek logs, normalized events, statuses и datasets — runtime artifacts в `output/`, не предназначенные для Git.

## Запуск

Перед использованием проверяйте реальный CLI: `python lab/sensor/run_v0_3_sensor_stage.py --help`.

## Проверки

Capture, correlation, aggregation, validator, provenance и split audits подтверждают техническую целостность campaign.

## Ограничения

Стенд не моделирует production network и не предназначен для внешних целей.

## Связанные документы

[Архитектура](../docs/architecture.md), [безопасность](../docs/safety-model.md), [воспроизводимость](../docs/reproducibility.md).

## Кампании v0.3.7

Стенд выполняет 12 training и 6 internal-validation runs только внутри Docker lab. Каждый run содержит 6 warm-up окон и 28 scored окон, сгруппированных в 14 двухоконных episodes. Marker-пакеты исключаются из aggregation; validation capture использует отдельный PCAP на execution, увеличенный kernel buffer и immediate mode, поэтому корреляция не зависит от нестабильности Docker wall-clock. Контрольный marker-журнал содержит только границы и provenance, не входит в признаки. Runtime PCAP, Zeek logs и datasets остаются вне Git.

## Кампании v0.3.8

Новые 12 training и 6 validation runs используют отдельные scenario IDs, seeds, Docker project `filin_v038_lab`, volumes и manifests. Получено 108 warm-up и 648 scored окон, 216 episodes и 756 пар markers/PCAP-интервалов. Validation собирается только после заморозки candidate; runtime PCAP, журналы и datasets не входят в Git.

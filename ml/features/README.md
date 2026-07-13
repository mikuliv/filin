# Признаки и datasets

## Назначение

Определение feature profiles, aggregation по scenario execution windows и profile-aware validation.

## Что реализовано

`client_core_v0_2` и `client_extended_v0_2` используют client observations. `network_sensor_v0_3` использует только correlated Zeek observations. Окна формируются по actual execution intervals; metadata и identifiers не являются model features.

## Основные файлы

- `schema.py` — единственный источник feature profiles;
- `build_windows_dataset.py` — client datasets;
- `build_network_sensor_dataset.py` — sensor dataset;
- `validators.py` — structure, provenance и arithmetic checks.

## Входные данные и выходные данные

Input — normalized/correlated events и execution metadata. Output CSV — runtime artifact в `lab/output/datasets/`.

## Запуск

`python ml/features/validators.py --help`

## Проверки

Client profiles не содержат packet/flow fields, которые недоступны client source. Sensor profile исключает label, execution IDs, marker fields, raw endpoints и Zeek UID.

## Ограничения

Packet/flow признаки требуют независимого sensor source; client events не используются для подмены Zeek observations.

## Связанные документы

[Происхождение данных](../../docs/data-provenance.md), [datasets](../../datasets/README.md).
# Historical and future sensor profiles

`network_sensor_v0_3` is preserved for reproduction of v0.3.1--v0.3.3. The
historical baseline did **not** use only its declared feature profile: its
numeric-column selector also included `window_index`, `window_event_count`,
`window_has_events`, and `window_duration_seconds`. That immutable historical
list is `HISTORICAL_V031_BASELINE_FEATURES` in `schema.py` and must not be
renamed as the declared v0.3 profile.

`network_sensor_v0_4` is a future, strict profile. Its ordered list in
`schema.py` is the sole source of model columns; v0.4 builders must not select
all numeric CSV columns or synthesize unavailable measures as zero.

## Causal profiles v0.3.7

`network_sensor_v0_5_temporal` добавляет к 16 rate/share признакам 25 delta, rolling median, robust-z, slope, periodicity и persistence признаков. `network_sensor_v0_5_contextual` добавляет 10 признаков response/retry/recovery/workflow. Builder использует только текущее и прошлые окна одного asset/run; future mutation, labels, warm-up flag и identity metadata не меняют model vector.

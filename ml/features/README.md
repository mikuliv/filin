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
## Historical and future sensor profiles

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

Имена некоторых исторических v0.5 признаков не выражают фактическую формулу:
`destination_set_jaccard_change` не является Jaccard distance,
`http_response_status_entropy` не является entropy, два `consecutive_*` не
измеряют непрерывную серию, а `failed_then_successful_connection_rate` не
проверяет порядок событий. Точные ограничения перечислены в
[`docs/limitations.md`](../../docs/limitations.md); исторические значения не
пересчитываются.

## Future integrity profile v0.6

`network_sensor_v0_6_integrity` предназначен только для новых executions.
Единственный ordered contract загружается из `feature_dictionary.yaml` через
`profile_registry.py`; builder обязан вызвать validator и зафиксировать schema,
builder, dataset, row-order, execution-mapping и marker-interval hashes.

В v0.3.8 evidence profile расширяет 51 contextual feature девятью причинными признаками availability/recovery. Все вычисления используют только текущее и предыдущие окна, state сбрасывается между runs, а identity, labels, scenario, seed, condition и будущие окна запрещены. Selection выбрал contextual control; это не отменяет проверку и доступность evidence profile для будущих новых циклов.

v0.3.9 намеренно использует неизменённый 51-признаковый contextual control: семантика, порядок и missing rules не меняются. Probability, conformal, support, episode phase и lifecycle являются post-model metadata и запрещены в X.
## Контракт v0.3.10

Профиль `network_sensor_v0_5_contextual_control` остаётся неизменным и содержит ровно 51 причинный признак при history depth 6. Probabilities, conformal values, support distances, pending state, alert history и episode metadata в X не входят.

Schema audit и future-mutation audit пройдены на v0.3.10. Frozen validation
дала closed-set macro F1 `1.0`; post-hoc drift всех 51 признаков рассчитан, но
не использовался для отбора, исключения строк или изменения candidate.

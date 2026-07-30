# Переоценка методологии v0.3.15.4–v0.3.15.5

## Статус документа

Этот документ уточняет научную интерпретацию уже зафиксированных результатов. Он не изменяет frozen-отчёты, прогнозы, метрики, модель или исторические решения. Проверяемый кандидат остаётся тем же артефактом `v03154:65a3dd912d845bc1`, но область доказанной применимости ограничивается исследованным синтетическим семейством.

## Краткий вердикт

| Вывод | Статус | Основание |
| --- | --- | --- |
| PCAP существуют, различаются по SHA-256 и обработаны Zeek 7.0.5 | ДОКАЗАНО | Проверки целостности кампаний и `run_campaign.py` |
| 51 входной признак вычисляется из `conn.log`, `http.log`, `dns.log` и причинного состояния | ДОКАЗАНО | `feature_v2.py:30-75`, `network_sensor_v0_5.py:27-47` |
| Арифметика frozen-прогнозов и метрик воспроизводится | ДОКАЗАНО | Независимый пересчёт опубликованных строк прогнозов и меток |
| Кандидат разделяет проверенный синтетический корпус | ДОКАЗАНО | Frozen-метрики и диагностические baselines |
| PCAP получены от реального Docker-клиента и целевого сервиса | ОПРОВЕРГНУТО | `run_campaign.py:49-106` непосредственно собирает пакеты Scapy; Docker запускает Zeek в `run_campaign.py:144-183` |
| v0.3.15.5 независим по семейству генератора | ОПРОВЕРГНУТО | `v0_3_15_5/run_campaign.py` повторно вызывает `v0_3_15_4.run_campaign.create_capture` |
| v0.3.15.5 проверяет независимую инфраструктуру | ОПРОВЕРГНУТО | Те же адреса, шаблоны, порт 80 и контейнер Zeek; `external_target_count: 0` |
| Идеальные метрики доказывают внешнюю или практическую точность | НЕ ПОДТВЕРЖДЕНО | Простые группы признаков также дают идеальное разделение, а семантика генератора общая |
| Кандидат готов к production | ОПРОВЕРГНУТО | Реальный сетевой клиент, независимая инфраструктура и внешний корпус не проверены |

## Фактическая цепочка данных

Заявленная техническая часть после PCAP подтверждается:

```text
PCAP → Zeek 7.0.5 → conn/http/dns JSON logs → окно → 51 признаков
→ frozen-модель → prediction → метрики
```

Полная фактическая цепочка происхождения данных иная:

```text
label vault → true_class → class-conditioned packet template → PCAP
→ Zeek → 51 признаков → frozen-модель → prediction → метрики
```

`capture_phase` читает `true_class` до создания PCAP (`ml/experiments/v0_3_15_4/run_campaign.py:109-128`). `_profile` задаёт почти фиксированные число HTTP-обменов, метод, статусы и интервалы по классу (`:65-70`), а `create_capture` задаёт адреса, порты, URI, ответы и порядок пакетов (`:73-106`). Контейнер Docker появляется только в `_zeek_session`, где запускается Zeek над уже созданным файлом (`:144-183`). Поэтому прямого текстового поля label в векторе нет, но причинный предок признаков зависит от label.

## Первичные материалы и достаточность

| Материал | Наличие/объём | Хранение | Достаточность |
| --- | --- | --- | --- |
| v0.3.15.4 PCAP | 5000; 5000 уникальных SHA-256 | runtime, не Git | Достаточно для проверки синтетического packet-level корпуса; недостаточно для реального client-to-service трафика |
| v0.3.15.4 Zeek logs | 5000 обработанных окон | runtime | Достаточно для повторного извлечения признаков |
| v0.3.15.4 feature rows | 4750 строк × 51 | runtime | Достаточно для диагностик при сохранении порядка |
| v0.3.15.4 labels/split | 4750 строк; 25 сессий; 15/5/5 | runtime + manifests | Достаточно для воспроизведения локальной оценки |
| v0.3.15.4 model binary | `runtime/v0_3_15_4/v03154_candidate.joblib`; SHA-256 из manifest | runtime, не Git | Целостность подтверждена; загрузка допустима только в доверенном локальном окружении |
| v0.3.15.5 PCAP | 4000; 4000 уникальных SHA-256; overlap с v0.3.15.4 = 0 | runtime, не Git | Новые байты, но не новое семейство генератора |
| v0.3.15.5 Zeek logs/features | 4000 обработанных PCAP; 3800 строк × 51 | runtime | Достаточно для воспроизведения локальной оценки |
| v0.3.15.5 predictions/labels | 3800 строк; 200 эпизодов | frozen/runtime набор | Достаточно для пересчёта опубликованных метрик |
| Внешний PCAP/Zeek corpus | отсутствует | — | Недостаточно для внешней валидности |
| Фактический Docker client/server capture | отсутствует для этих стадий | — | Недостаточно для проверки реального исполнения сценария |

Необходимость первичных runtime-материалов означает, что одна копия Git без соответствующего локального хранилища не обеспечивает полный независимый повтор.

## Все 51 признаков

Общие правила: тип всех входов — конечное `float`; окно — 1 с; нули и отсутствующие счётчики нормализуются в `0`, деление защищено минимумом; история — до четырёх предыдущих окон той же сессии; будущие события не используются. `conn.log` даёт потоки, состояния, байты, пакеты, адрес назначения, порт, протокол, время и duration; `http.log` — запросы, методы и статусы; `dns.log` — число запросов. Код: базовые формулы `ml/features/v034_profiles.py:67-95`, временные и контекстные `ml/features/network_sensor_v0_5.py:27-47`, адаптер Zeek `ml/experiments/v0_3_15_4/feature_v2.py:30-75`.

| № | Точное имя | Источник и формула | Единицы/история | Риск proxy/fingerprint/leakage | Оценка |
| ---: | --- | --- | --- | --- | --- |
| 1 | `failed_connection_rate` | conn: failed/flows | доля; текущее | class profile/connection template | высокий |
| 2 | `udp_flow_share` | conn: udp/flows | доля; текущее | protocol template | средний |
| 3 | `tcp_flow_share` | conn: tcp/flows | доля; текущее | protocol template | средний |
| 4 | `http_requests_per_flow` | http+conn: requests/flows | запрос/поток; текущее | HTTP template | высокий |
| 5 | `dns_requests_per_flow` | dns+conn: queries/flows | запрос/поток; текущее | infrastructure mix | средний |
| 6 | `events_per_second` | conn+http+dns: event count/1 s | событий/с; текущее | fixed activity profile | высокий |
| 7 | `flows_per_second` | conn: flows/1 s | потоков/с; текущее | fixed flow count | высокий |
| 8 | `bytes_per_flow` | conn: (orig+resp bytes)/flows | байт/поток; текущее | payload/response template | высокий |
| 9 | `packets_per_flow` | conn: (orig+resp packets)/flows | пакет/поток; текущее | exchange template | высокий |
| 10 | `orig_bytes_per_flow` | conn: orig bytes/flows | байт/поток; текущее | request template | высокий |
| 11 | `resp_bytes_per_flow` | conn: resp bytes/flows | байт/поток; текущее | response template | высокий |
| 12 | `failed_connections_per_second` | conn: failed/1 s | соединений/с; текущее | class profile | высокий |
| 13 | `unique_destinations_per_flow` | conn: unique resp_h/flows | доля; текущее | fixed topology | высокий |
| 14 | `unique_services_per_flow` | conn: unique (proto,port)/flows | доля; текущее | ports/services | критический |
| 15 | `response_bytes_share` | conn: resp/(orig+resp bytes) | доля; текущее | response direction/template | высокий |
| 16 | `orig_packet_share` | conn: orig/(orig+resp packets) | доля; текущее | exchange direction | высокий |
| 17 | `delta_flows_per_second` | current fps − previous fps | потоков/с; 1 прошлое | schedule transition | высокий |
| 18 | `flows_per_second_to_rolling_median` | fps/median(previous ≤4 fps) | отношение; 4 прошлых | schedule/profile | высокий |
| 19 | `robust_z_flows_per_second` | (fps−median)/1.4826·MAD previous ≤4 | z; 4 прошлых | schedule/profile | высокий |
| 20 | `delta_events_per_second` | current eps − previous eps | событий/с; 1 прошлое | schedule transition | высокий |
| 21 | `events_per_second_to_rolling_median` | eps/median(previous ≤4 eps) | отношение; 4 прошлых | schedule/profile | высокий |
| 22 | `robust_z_events_per_second` | robust z over previous ≤4 eps | z; 4 прошлых | schedule/profile | высокий |
| 23 | `delta_failed_connections_per_second` | current failure rate − previous | соединений/с; 1 прошлое | episode boundary | высокий |
| 24 | `failed_connections_to_rolling_median` | failure/median(previous ≤4) | отношение; 4 прошлых | episode boundary | высокий |
| 25 | `robust_z_failed_connections` | robust z over previous ≤4 failures | z; 4 прошлых | episode boundary | высокий |
| 26 | `delta_bytes_per_flow` | current bpf − previous bpf | байт/поток; 1 прошлое | payload transition | высокий |
| 27 | `bytes_per_flow_to_rolling_median` | bpf/median(previous ≤4 bpf) | отношение; 4 прошлых | payload profile | высокий |
| 28 | `delta_packets_per_flow` | current ppf − previous ppf | пакет/поток; 1 прошлое | exchange transition | высокий |
| 29 | `packets_per_flow_to_rolling_median` | ppf/median(previous ≤4 ppf) | отношение; 4 прошлых | exchange profile | высокий |
| 30 | `delta_unique_destinations_per_flow` | current destination ratio − previous | доля; 1 прошлое | topology/schedule | высокий |
| 31 | `destination_set_jaccard_change` | min(1, abs(current destination ratio−previous)) | proxy-доля; 1 прошлое | не истинный Jaccard; topology | высокий |
| 32 | `protocol_mix_l1_change` | abs(Δudp share)+abs(Δtcp share) | L1; 1 прошлое | protocol transition | средний |
| 33 | `response_bytes_share_change` | current response share − previous | доля; 1 прошлое | response transition | высокий |
| 34 | `udp_flow_share_change` | current udp share − previous | доля; 1 прошлое | protocol transition | средний |
| 35 | `consecutive_high_failure_windows` | count(history failure>.5)+current indicator | окон; 4 прошлых | episode position | высокий |
| 36 | `consecutive_high_flow_windows` | history count above history median + 1 | окон; 4 прошлых | episode position; формула не проверяет current | высокий |
| 37 | `rolling_activity_slope` | linear slope(previous ≤4 fps + current) | потоков/с на окно; 4 прошлых | scenario timing | высокий |
| 38 | `rolling_failure_slope` | linear slope(previous ≤4 failures + current) | соединений/с на окно; 4 прошлых | scenario timing | высокий |
| 39 | `request_spacing_cv` | std(conn start spacing)/mean | безразмерно; текущее | timing template | критический |
| 40 | `periodicity_stability` | 1−abs(current periodicity−previous) | безразмерно; 1 прошлое | timing template | критический |
| 41 | `long_lived_flow_persistence` | current duration>1 + count(history long) | окон; 4 прошлых | duration template | высокий |
| 42 | `success_response_share` | http 2xx/http requests | доля; текущее | fixed status code | критический |
| 43 | `failed_then_successful_connection_rate` | min(success,failed)/flows | доля; текущее | connection template | высокий |
| 44 | `retry_recovery_rate` | success/(failed+success) | доля; текущее | connection template | высокий |
| 45 | `target_responsiveness_ratio` | 1−HTTP error rate | доля; текущее | fixed status code | критический |
| 46 | `connection_completion_rate` | successful/flows | доля; текущее | connection template | высокий |
| 47 | `long_lived_flow_share` | indicator(max duration>1)/flows | доля; текущее | duration template | высокий |
| 48 | `http_method_diversity` | (GET present + POST present)/2 | доля; текущее | class-fixed method | критический |
| 49 | `http_response_status_entropy` | count(present status families 2xx/4xx/5xx)/3 | proxy, не Shannon entropy; текущее | class-fixed status | критический |
| 50 | `response_direction_balance` | 1−2·abs(.5−response byte share) | доля; текущее | response template | высокий |
| 51 | `service_availability_recovery_evidence` | indicator(success>0 and failed>0) | бинарное; текущее | connection template | высокий |

Все признаки прослежены до Zeek-полей или детерминированной истории. Темпоральной утечки в смысле использования будущих окон не найдено. При этом высокий риск class-conditioned proxy сохраняется: сами наблюдаемые события были созданы по label-зависимому шаблону.

## Split v0.3.15.4 revision 2

Каждая строка содержит 200 PCAP, 190 оцениваемых окон, seed из manifest, один и тот же Scapy-генератор, адреса `10.31.54.10→10.31.54.20`, основной HTTP-порт 80 и одинаковую схему эпизодов. Suffix определяет split: `001–003` — train, `004` — calibration, `005` — internal audit.

| session_id | group | seed | split | PCAP | окна | эпизоды | revision |
| --- | --- | ---: | --- | ---: | ---: | ---: | --- |
| `dev2_scenario_semantics_001` | scenario_semantics | 21101 | train | 200 | 190 | 8 | r2 |
| `dev2_scenario_semantics_002` | scenario_semantics | 21102 | train | 200 | 190 | 8 | r2 |
| `dev2_scenario_semantics_003` | scenario_semantics | 21103 | train | 200 | 190 | 8 | r2 |
| `dev2_scenario_semantics_004` | scenario_semantics | 21104 | calibration | 200 | 190 | 8 | r2 |
| `dev2_scenario_semantics_005` | scenario_semantics | 21105 | internal audit | 200 | 190 | 8 | r2 |
| `dev2_feature_provenance_001` | feature_provenance | 21201 | train | 200 | 190 | 8 | r2 |
| `dev2_feature_provenance_002` | feature_provenance | 21202 | train | 200 | 190 | 8 | r2 |
| `dev2_feature_provenance_003` | feature_provenance | 21203 | train | 200 | 190 | 8 | r2 |
| `dev2_feature_provenance_004` | feature_provenance | 21204 | calibration | 200 | 190 | 8 | r2 |
| `dev2_feature_provenance_005` | feature_provenance | 21205 | internal audit | 200 | 190 | 8 | r2 |
| `dev2_subtype_boundary_001` | subtype_boundary | 21301 | train | 200 | 190 | 8 | r2 |
| `dev2_subtype_boundary_002` | subtype_boundary | 21302 | train | 200 | 190 | 8 | r2 |
| `dev2_subtype_boundary_003` | subtype_boundary | 21303 | train | 200 | 190 | 8 | r2 |
| `dev2_subtype_boundary_004` | subtype_boundary | 21304 | calibration | 200 | 190 | 8 | r2 |
| `dev2_subtype_boundary_005` | subtype_boundary | 21305 | internal audit | 200 | 190 | 8 | r2 |
| `dev2_conformal_behavior_001` | conformal_behavior | 21401 | train | 200 | 190 | 8 | r2 |
| `dev2_conformal_behavior_002` | conformal_behavior | 21402 | train | 200 | 190 | 8 | r2 |
| `dev2_conformal_behavior_003` | conformal_behavior | 21403 | train | 200 | 190 | 8 | r2 |
| `dev2_conformal_behavior_004` | conformal_behavior | 21404 | calibration | 200 | 190 | 8 | r2 |
| `dev2_conformal_behavior_005` | conformal_behavior | 21405 | internal audit | 200 | 190 | 8 | r2 |
| `dev2_benign_hard_negatives_001` | benign_hard_negatives | 21501 | train | 200 | 190 | 8 | r2 |
| `dev2_benign_hard_negatives_002` | benign_hard_negatives | 21502 | train | 200 | 190 | 8 | r2 |
| `dev2_benign_hard_negatives_003` | benign_hard_negatives | 21503 | train | 200 | 190 | 8 | r2 |
| `dev2_benign_hard_negatives_004` | benign_hard_negatives | 21504 | calibration | 200 | 190 | 8 | r2 |
| `dev2_benign_hard_negatives_005` | benign_hard_negatives | 21505 | internal audit | 200 | 190 | 8 | r2 |

Итого: 25 сессий, 5000 PCAP, 4750 оцениваемых окон, 200 эпизодов; 15/5/5 сессий. Revision 1 исключала класс из части split и потому не обеспечивала сопоставимую классовую поддержку. Revision 2 устранила явное omission, однако suffix полностью кодирует роль split, а generator family, target, инфраструктура и шаблоны классов между частями не разделены.

## Prospective holdout v0.3.15.5

Каждая сессия содержит 200 PCAP, 190 оцениваемых окон и 10 эпизодов. Фактический генератор и target те же, что в v0.3.15.4; различаются идентификаторы, seeds, timestamps, nonces и хеши.

| session_id | group | seed | PCAP | окна | эпизоды | отличие от train |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| `holdout_balanced_001` | balanced | 22101 | 200 | 190 | 10 | новый seed/id |
| `holdout_balanced_002` | balanced | 22102 | 200 | 190 | 10 | новый seed/id |
| `holdout_balanced_003` | balanced | 22103 | 200 | 190 | 10 | новый seed/id |
| `holdout_balanced_004` | balanced | 22104 | 200 | 190 | 10 | новый seed/id |
| `holdout_auth_generalization_001` | auth_generalization | 22201 | 200 | 190 | 10 | новый seed/id |
| `holdout_auth_generalization_002` | auth_generalization | 22202 | 200 | 190 | 10 | новый seed/id |
| `holdout_auth_generalization_003` | auth_generalization | 22203 | 200 | 190 | 10 | новый seed/id |
| `holdout_auth_generalization_004` | auth_generalization | 22204 | 200 | 190 | 10 | новый seed/id |
| `holdout_web_probe_generalization_001` | web_probe_generalization | 22301 | 200 | 190 | 10 | новый seed/id |
| `holdout_web_probe_generalization_002` | web_probe_generalization | 22302 | 200 | 190 | 10 | новый seed/id |
| `holdout_web_probe_generalization_003` | web_probe_generalization | 22303 | 200 | 190 | 10 | новый seed/id |
| `holdout_web_probe_generalization_004` | web_probe_generalization | 22304 | 200 | 190 | 10 | новый seed/id |
| `holdout_background_shift_001` | background_shift | 22401 | 200 | 190 | 10 | новый seed/id |
| `holdout_background_shift_002` | background_shift | 22402 | 200 | 190 | 10 | новый seed/id |
| `holdout_background_shift_003` | background_shift | 22403 | 200 | 190 | 10 | новый seed/id |
| `holdout_background_shift_004` | background_shift | 22404 | 200 | 190 | 10 | новый seed/id |
| `holdout_runtime_resilience_001` | runtime_resilience | 22501 | 200 | 190 | 10 | новый seed/id |
| `holdout_runtime_resilience_002` | runtime_resilience | 22502 | 200 | 190 | 10 | новый seed/id |
| `holdout_runtime_resilience_003` | runtime_resilience | 22503 | 200 | 190 | 10 | новый seed/id |
| `holdout_runtime_resilience_004` | runtime_resilience | 22504 | 200 | 190 | 10 | новый seed/id |

Итого: 20 сессий, 4000 PCAP, 3800 оцениваемых окон, 200 эпизодов. `scenario_variant_manifest.yaml` содержит новые parameter vectors, но основной генератор получает лишь вычисленный `variant`, а `_profile(class_name, variant)` игнорирует variant для всех attack-классов. Поэтому `spacing_ms`, `payload_size`, `response_order`, `timeout_mode`, `background_level` и заявленные attack counts не подтверждены наблюдаемым PCAP.

## Независимый пересчёт и диагностические baselines

Frozen predictions и раскрытые labels дали те же агрегаты и confusion matrices, что опубликованы: расхождений арифметики не найдено. Это подтверждает вычисление метрик, но не независимость данных.

| Диагностика | Internal audit accuracy / macro-F1 | v0.3.15.5 accuracy / macro-F1 | Интерпретация |
| --- | --- | --- | --- |
| Majority | .8947 / .1574 | .9079 / .1586 | Дисбаланс классов велик |
| Ports/services logistic | 1.0000 / 1.0000 | 1.0000 / 1.0000 | Классы кодируются сервисным профилем |
| Traffic intensity logistic | 1.0000 / 1.0000 | 1.0000 / 1.0000 | Интенсивность сама разделяет классы |
| HTTP-only logistic | 1.0000 / 1.0000 | 1.0000 / 1.0000 | HTTP-шаблон сам разделяет классы |
| Temporal logistic | 1.0000 / 1.0000 | 1.0000 / 1.0000 | Расписание/переходы сохраняют fingerprint |
| Rolling/history logistic | 1.0000 / 1.0000 | 1.0000 / 1.0000 | История не устраняет простое разделение |
| Timing logistic | .9716 / .8658 | .9934 / .9513 | Временной шаблон почти достаточен |
| Recovery logistic | .9368 / .4406 | .9447 / .4411 | Контекст ответа даёт сильный сигнал |
| All-51 nearest centroid | .9916 / .9306 | .9921 / .9251 | Сложная модель не обязательна |
| All-51 tree depth 3 | .9579 / .5833 | .9632 / .5833 | Неглубокие правила дают высокий accuracy |
| Suffix/session position logistic | .4053 / .2624 | .5111 / .1664 | Прямой suffix слаб, но split им детерминирован |

## Frozen-модель

- ДОКАЗАНО: SHA-256 файла соответствует `ml/artifacts/v0_3_15_4/candidate_manifest.json:2-6`.
- ДОКАЗАНО: архитектура — gate и subtype на `HistGradientBoostingClassifier`, затем sigmoid calibration и class-conditional thresholds (`train_candidate.py:67-140`).
- СИЛЬНО ПОДТВЕРЖДЕНО: named DataFrame сохраняет исследованную offline/runtime совместимость.
- ОПРОВЕРГНУТО: идентификатор внутри bundle не совпадает с окончательным внешним ID. В `train_candidate.py:130-131` ID вычисляется до повторной сериализации, затем файл меняется и внешний ID вычисляется снова без обновления поля bundle.
- ОПРОВЕРГНУТО: фактический порядок обучения не гарантирован как порядок YAML-контракта. Feature JSONL записывается с `sort_keys=True` (`run_campaign.py:34-38`), а `names = list(dev_rows[0]["features"])` (`train_candidate.py:93-98`) принимает этот порядок, то есть алфавитный порядок сериализованного объекта.
- НЕИЗВЕСТНО: точная версия scikit-learn обучения. Manifest фиксирует Python 3.13 и joblib 1.5.3, но не scikit-learn; текущая локальная версия 1.8.0 не доказывает версию создания объекта.

## Семантическая независимость

| Свойство | Train | Calibration | Internal audit | Prospective holdout |
| --- | --- | --- | --- | --- |
| Generator family/code | тот же Scapy `_profile/create_capture` | тот же | тот же | импортирует тот же |
| Target services/ports | фиксированные шаблоны | те же | те же | те же |
| HTTP paths/statuses | class-conditioned | те же семейства | те же семейства | те же функции |
| Timing/duration | class-conditioned | то же распределение | то же | те же функции |
| Seeds/identifiers | 211xx–215xx, suffix 001–003 | suffix 004 | suffix 005 | 221xx–225xx, новые IDs |
| Infrastructure | фиксированные IP/MAC, локальный Zeek | та же | та же | та же |
| Scenario order | общий schedule family | общий | общий | новый manifest, та же реализация профиля |
| Background traffic | шаблонный | шаблонный | шаблонный | параметр заявлен, но не реализован в attack PCAP |
| Feature contract | 51 | 51 | 51 | те же 51 |
| Label process | label выбирает packet template | то же | то же | то же |

Непересечение SHA, seed, session_id и времени запуска подтверждено. Семантическое непересечение generator family, infrastructure, target, response template и label mechanism опровергнуто. Следовательно, split достаточен для проверки воспроизводимости на новых экземплярах того же генератора, но недостаточен для заявления об обобщении.

## Риски

- Прямая утечка label в 51-мерной таблице: НЕ ПОДТВЕРЖДЕНО.
- Косвенная утечка через label-conditioned создание наблюдений: СИЛЬНО ПОДТВЕРЖДЕНО.
- Fingerprint генератора: ДОКАЗАНО.
- Fingerprint инфраструктуры: СИЛЬНО ПОДТВЕРЖДЕНО как неразделённый фактор; его самостоятельный вклад НЕИЗВЕСТЕН.
- Расписание и положение окна: СИЛЬНО ПОДТВЕРЖДЕНО как proxy; suffix отдельно слаб, но детерминирует split.
- Будущие данные в 51 признаке: ОПРОВЕРГНУТО; используются текущее и до четырёх прошлых окон.
- Ошибка арифметики метрик: ОПРОВЕРГНУТО.
- Выбор после просмотра prospective labels: НЕ ПОДТВЕРЖДЕНО для frozen-кандидата; после раскрытия v0.3.15.5 эти данные нельзя повторно считать слепым holdout.

## Утверждения, которые сохраняются

Можно сохранять утверждения, что:

- целостность frozen-артефакта проверена;
- PCAP обработаны Zeek, а модель получает 51 вычисленный сетевой признак;
- published predictions и метрики арифметически воспроизводимы;
- кандидат успешно разделяет конкретный синтетический корпус и пригоден как техническое доказательство конвейера;
- runtime/transport contracts могут проверяться отдельно от качества обнаружения.

## Утверждения, которые ограничиваются

- `independent` и `prospective` означают только процедурное разделение идентификаторов и момента раскрытия меток;
- точность относится только к проверенному синтетическому корпусу того же generator family;
- runtime и transport validation подтверждают соответствующие технические контракты, но не качество обнаружения на новом сетевом распределении.

## Утверждения, которые отменяются

- семантически независимый holdout;
- новая generator family в v0.3.15.5;
- независимая инфраструктура;
- подтверждённая внешняя валидность;
- production-готовность;
- практическая точность, следующая непосредственно из идеальных frozen-метрик.

## Минимальный следующий эксперимент

Следующий допустимый эксперимент описан в [протоколе независимой сетевой проверки](next_independent_network_validation_protocol.md). До его выполнения научный статус кандидата — frozen технический артефакт, проверенный только на одном синтетическом семействе.

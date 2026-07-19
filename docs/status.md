# Текущий статус

Авторитетный источник: [`research-state.yaml`](research-state.yaml).

- Последний завершённый этап: v0.3.12.
- Итог последнего этапа: frozen multi-benchmark regression завершена, но не пройдена.
- Интеграция с backend разрешена: нет.
- Теневой режим разрешён: нет.
- Готовность к промышленной эксплуатации: нет.

Этап v0.3.11 завершён: 12 training и 6 prospective internal-validation runs,
792 и 396 уникальных capture hashes, заморозка кандидата до validation collection
и единственная no-fit immutable prediction. Все scientific policies пройдены;
разрешена только frozen regression v0.3.12, backend и shadow mode запрещены.

## v0.3.12

Frozen regression выполнена без обучения, калибровки, tuning, Docker, Zeek и feature extraction. Core prediction допустима только для v0.3.9 и v0.3.10; их macro F1 равна `0.990734` и `1.000000`, benign recall — `1.0`, FPR — `0.0`, episode recall/precision — `1.0/1.0`. Detection by second window равна `0.733333` на обоих наборах и ниже gate `0.75`.

v0.3.6 и v0.3.7 не имеют frozen 51-feature table. v0.3.8 содержит 216 строк вместо 252, поэтому prediction запрещена. `evaluation_coverage_policy_passed=false`, `all_episode_gates_passed=false`, `v0312_regression_passed=false`, readiness к v0.3.13 — false.

## v0.3.6

Prospective holdout завершён с отрицательным результатом: 12 runs, 252 locked windows,
`candidate_ready_for_shadow_mode=false`, `model_refit_on_v036=false` и
`sensor_ready_for_backend_integration=false`. Shadow mode и backend integration запрещены.

> **v0.3.3 negative result:** benign recall `0.000`, false positive rate
> `1.000`, and backend ML integration is prohibited. The backend is a
> historical demonstration prototype. MITRE ATT&CK, Sigma, SIEM and analyst
> interface are not confirmed production pipelines.

| Компонент | Состояние | Последняя подтверждённая версия | Подтверждение | Ограничения |
| --- | --- | --- | --- | --- |
| Docker laboratory | Готово | v0.3 | Изолированные campaign runs | Только лабораторная сеть |
| Безопасные сценарии | Готово | v0.3 | Manifest и execution records | Не являются реальными атаками |
| Marker-aware executions | Готово | v0.3 | Start/end markers и sensor intervals | Markers не являются features |
| Passive capture | Готово | v0.3 | Capture-sidecar и PCAP audit | Нет production capture |
| PCAP storage | Готово | v0.3 | Docker-managed volume и hashes | Runtime artifacts вне Git |
| Zeek offline processing | Готово | v0.3 | PCAP→Zeek logs | Ограничено видимостью стенда |
| `network_sensor_v0_3` | Готово | v0.3 | Builders, validators, audits | Ограниченный набор сервисов |
| Independent train/test campaign | Готово | v0.3 | 6 train + 3 test runs | Лабораторный support |
| Frozen baseline evaluation | Экспериментально подтверждено | v0.3.1 | Pooled external test | Не production validation |
| Robustness evaluation | Экспериментально подтверждено | v0.3.2 | 12 external robustness-runs | Controlled shifts, identical metrics требуют осторожности |
| Environment evaluation v0.3.3 | Завершено с отрицательным результатом | v0.3.3 | Bridge validation и forensic audit | Benign recall `0.000`; backend integration запрещена |
| Backend model integration | Не начато | — | — | Нельзя считать backend готовым |
| v0.3.4 benign redesign | Реализована конфигурация research-этапа | v0.3.4 | Isolation policy, three profiles, grouped CV/freeze | Результаты кампаний являются runtime artifacts; backend не меняется |
| MITRE ATT&CK mapping | Запланировано | — | — | Будущая работа |
| Sigma generation | Запланировано | — | — | Будущая работа |
| SIEM integration | Запланировано | — | — | Будущая работа |
| Production validation | Не выполнено | — | — | Отсутствуют production data и deployment procedure |

## v0.3.7

Реализован новый изолированный training/validation cycle иерархического сенсора. Итоговый научный статус определяется frozen policy report; независимо от метрик `candidate_ready_for_shadow_mode=false` и `sensor_ready_for_backend_integration=false`. v0.3.6 остаётся неизменяемым regression benchmark для возможного v0.3.8, но в v0.3.7 не открывается для tuning.

## v0.3.8

Class-conditional uncertainty cycle завершён полностью. Frozen validation дала
macro F1 `0.990734`, FPR `0.000000`, episode recall `0.933333`, unresolved rate
`0.066667` и attack-window alert recall `0.600000`. Closed-set, conformal и
support gates пройдены, window и episode gates не пройдены. Поэтому
`v0_3_8_policy_passed=false`, `ready_for_v0_3_9=false`, backend integration и
shadow mode запрещены.

## v0.3.9

Episode-first цикл завершён полностью: training 12/12 (`504` scored windows,
`168` episodes, `576` marker pairs) и validation 6/6 (`252`, `84`, `288`).
Candidate `decision:f5e327a3497c:hgb:hgb` заморожен до validation, lock создан
до единственной prediction; validation fit-call count равен `0`.

Closed-set macro F1 `0.990734`, benign recall `1.000000`, FPR `0.000000`;
strong-evidence precision `1.000000`, recall `0.600000`. При этом review rate
`0.416667`, true-class evidence window recall `0.655556`, attack episode recall
`0.700000`, detection by second window `0.666667`, unresolved rate `0.300000` и
support top-2 rate `0.607143`. Frozen policy отрицательна:
`v039_internal_validation_passed=false` и
`candidate_ready_for_v0_3_10_regression=false`. Backend integration и shadow
mode запрещены.

Integrity-оговорка: core validation lock был создан до prediction, но его
`capture_hashes` ошибочно читались из `sensor/` и оказались пусты. После
prediction добавлены hashes 288 неизменённых PCAP из `captures/`; prediction не
повторялась. Исходный и исправленный lock hashes сохранены в audit.

## v0.3.10

Minimal probability-conformal cycle завершён полностью: training 12/12
(`648` scored windows, `216` episodes, `720` marker/capture intervals) и
validation 6/6 (`324`, `108`, `360`). Candidate
`minimal:8cd02e11bdda:hgb:hgb` заморожен до validation collection; все
`360/360` hashes из canonical `captures/` вошли в pre-prediction lock.

Frozen validation дала closed-set macro F1 `1.000000`, benign recall
`1.000000`, FPR `0.000000`, strong precision/recall `1.000000/1.000000`,
attack episode recall `1.000000`, episode alert precision `1.000000`, benign
episode false-alert rate `0.000000` и first-window detection `1.000000`.
Однако overall pending rate `0.370370` и attack pending rate `0.666667`
нарушают frozen pending/review policy; кроме того, training-only
`model_selection_policy_passed=false`. Поэтому
`v0310_internal_validation_passed=false` и
`candidate_ready_for_v0_3_11_regression=false`. Пороговые значения после
validation не менялись; backend integration и shadow mode запрещены.
# Техническое уточнение v0.3.10.1

Аудит показал, что 120 legacy pending окон validation являются post-alert continuation с корректным duplicate suppression, а burden-aware pending равен нулю. Это диагностическое уточнение не переписывает frozen policy: internal validation, regression readiness, shadow mode и backend integration остаются `false`.

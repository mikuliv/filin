# История разработки

Актуализация v0.3.15.1: corrective runtime audit завершён; integrated exporter исправлен, исторический bundle v0.3.15 сохранён, а v0.3.16 заблокирован до нового evidence-bearing runtime trial.

## v0.3.14

Добавлены passive event schema, canonical identities, hash chains, local sinks, bounded priority queue, checksum spool, checkpoint/retry/rate limit, privacy/fail-safe/backend audits, deterministic replay и fault/load campaigns.

## v0.3.13

Добавлены frozen prospective protocol, пять environmental groups, Docker-кампания, capture/input locks, sealed label vault, immutable prediction, causal evaluation, 5000 bootstrap iterations и regression bundle. Этап завершён положительно без изменения candidate.

## 19 июля 2026 — v0.3.12.2

Добавлен новый frozen regression protocol с обязательным causal order, восстановлен полный v0.3.8 bundle и один immutable prediction, переиспользованы прогнозы v0.3.9/v0.3.10. Все научные gates пройдены; разрешён v0.3.13 blind holdout при сохранении запрета backend/shadow mode.

## 13 июля 2026 — v0.3.6

Holdout был заблокирован до единственного predict, candidate не переобучался. Policy не пройдена
из-за benign recall `0.625` и FPR `0.375`; результат сохранён без изменения модели.

> Historical interpretation: v0.3.1 showed transfer inside the original
> laboratory campaign; v0.3.2 tested controlled robustness; v0.3.3 added a
> harder benign environment shift and preserved a negative result. These do not
> establish production readiness.

| Версия | Цель и результат | Данные и проверки | Ограничение |
| --- | --- | --- | --- |
| v0.2.2 | Source-aware profiles и окна по actual execution intervals. | Docker client observations, validators и aggregation audits. | Недостаточно независимых attack executions для ML. |
| v0.2.3 | Независимые train/test Docker-runs. | Campaign manifests, hashes и split discipline. | Client observations не являются независимым sensor source. |
| v0.2.4 | Baseline client profiles. | Независимые runs и external evaluation. | Client profile не перенёсся надёжно на test. |
| v0.3 | Независимый Zeek sensor pipeline. | 9 runs, 117 windows, PCAP→Zeek pipeline, marker correlation. | Лабораторная топология и ограниченный support. |
| v0.3.1 | Сравнение client и `network_sensor_v0_3`. | 6 train, 3 test runs; LORO и external test. | Результаты не подтверждают production readiness. |
| v0.3.2 | Внешняя robustness evaluation frozen baseline. | 12 runs, 156 windows, topology/background/temporal/combined shifts. | Идентичность метрик между runs требует осторожной интерпретации. |
| v0.3.3 | Forensic external environment evaluation frozen baseline. | 12 runs, 204 windows, bridge validation и reconstruction B. | Полный collapse benign-класса; policy не пройдена, модель не переобучалась. |
| v0.3.4 | Переработка benign representation. | Раздельные 12/6 campaigns, fixed profiles, grouped CV и candidate freeze. | Внешняя regression evaluation перенесена в v0.3.5. |

Связанные подтверждённые коммиты: `509b4f0` (passive capture), `e2a5dad` (campaign), `3ea23f9` (audits), `0428177` (baseline) и `9f40b58` (robustness evaluation).

11 июля 2026 года история платформы была технически выделена в отдельный репозиторий. После фильтрации Git идентификаторы коммитов изменились; сведения о выделении и ограничениях приведены в [документе о миграции](repository-migration.md).

## v0.3.7

Flat multiclass архитектура v0.3.4 показала систематические benign→attack ошибки на v0.3.6. Новый цикл ввёл causal temporal/contextual profiles, отдельные detection и subtype stages, group-aware sigmoid calibration, benign-only IsolationForest OOD guard, abstention и temporal evidence. Training и validation каталоги не пересекаются; candidate и policy фиксируются до первого validation prediction.

## v0.3.8

14 июля 2026 года выполнен полный class-conditional evidence cycle. Собраны 12 новых training и 6 новых validation runs, проведён nested grouped selection, заморожены candidate/validation manifests и один раз сформированы immutable predictions. Из 51-признакового control и 60-признакового evidence profile выбран control: дополнительные evidence-признаки не дали достаточного преимущества. Итоговая policy отрицательна из-за window/episode gates, поэтому продолжение в виде frozen regression v0.3.9 не открыто.

## v0.3.9

После отрицательного v0.3.8 создан новый цикл, а не regression replay. Base model и feature profile заранее фиксированы; новый decision layer разделяет window evidence, pending state, active alert, review и detection latency. Continuous class-support заменяет обязательное бинарное пересечение, а lifecycle допускает strong first-window promotion и требует повторения weak evidence.

15 июля 2026 года завершены 12 training и 6 prospective validation runs,
training-only selection 8/8/32, candidate freeze, validation lock и единственная
no-fit prediction. Closed-set и strong-evidence gates пройдены, но operational
episode/window и support gates — нет. Результат зафиксирован отрицательным;
v0.3.10 regression, backend integration и shadow mode не разрешены.
# v0.3.10

После технически корректной, но отрицательной v0.3.9 decision layer сокращён до двух причинных promotion paths и однократного alert emission. Новый цикл использует только собственные training и prospective validation rows. Capture lock теперь fail-closed требует все 360 hashes до единственной prediction и запрещает post-hoc дополнение.

16 июля 2026 года завершены 12 training и 6 validation runs, nested grouped
selection 6×4, candidate freeze, полный pre-prediction capture lock и no-fit
evaluation. Candidate дал macro F1 и episode recall `1.0` без benign false
alerts, но frozen training-selection и pending/review policies не прошёл:
attack pending rate `0.666667`. Результат зафиксирован отрицательным; v0.3.11
regression, backend integration и shadow mode не разрешены.
# v0.3.10.1

Выполнен read-only аудит frozen v0.3.10: проверены 12 SHA-256, причинно восстановлена семантика 324 validation окон, повторно оценены 101 grouped-OOF policies без fit, добавлены параллельный evaluator, resource monitoring, checkpoint/resume и controlled benchmark 1/3/6/8 workers. Научный статус v0.3.10 не изменён.

# v0.3.11

Реализован новый burden-aware training/validation cycle с эпизодами длины 2 и 4, раздельными pre-alert pending и post-alert continuation, nested grouped selection и 92-policy grid. Собраны 792 training и 396 validation captures, candidate заморожен до prospective validation, выполнена одна no-fit immutable prediction. Все frozen scientific policies пройдены; regression v0.3.12 разрешена, backend и shadow mode остаются запрещены.
# v0.3.12

Добавлен frozen multi-benchmark regression runner с read-only/no-fit guards, двухфазным доступом, compatibility audit, immutable predictions, run-level bootstrap и historical comparison. Этап завершён отрицательно: оценены v0.3.9/v0.3.10, три старых набора заблокированы, coverage и episode gates не пройдены.

# v0.3.12.1

Добавлен технический аудит причинности episode latency, state machine, activity key, дискретности gate и provenance v0.3.8. Созданы historical artifact inventory, recoverability classification, стандарт regression bundle, template и validator. Frozen v0.3.12 не изменён.

# v0.3.15

Добавлен локальный continuous shadow orchestration layer: canonical capture, containerized Zeek, frozen 51-feature extraction, online inference, causal state, `shadow_event_v1`, local sink, fault/restart recovery, blind post-hoc metrics и immutable shadow trial bundle.

# История разработки

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

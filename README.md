# Платформа «Филин»

Исследовательская платформа воспроизводимого анализа сетевых наблюдений.

> **Текущий статус**
>
> - Последний завершённый этап: **v0.3.18**.
> - Результат этапа: **completed / passed**.
> - Следующий допустимый этап: **v0.3.19 — package review**.
> - Фактический external trial пока запрещён.
> - Production readiness не заявляется.

Machine-readable источник статуса:
[`docs/status/project-status.yaml`](docs/status/project-status.yaml).

## О проекте

«Филин» исследует, как строить проверяемый анализ сетевых наблюдений без
смешивания обучения, оценки и runtime-доказательств. Платформа преобразует
контролируемый сетевой трафик в causal features, применяет замороженный
кандидат, формирует stateful episode decisions и выпускает пассивные события.

Исследовательская задача включает не только predictive behavior. Для каждого
этапа фиксируются contracts, identities, protocols, test gates и evidence.
Отрицательные результаты сохраняются, а исправления оформляются новой revision
или отдельным corrective stage.

Causal features используют только сведения, доступные к моменту prediction.
Frozen inference не допускает fit, calibration или threshold selection во
время evaluation. Evidence bundles связывают claims с проверяемыми manifests и
hash commitments.

Проект не является готовым средством защиты, production-сервисом, SIEM или
системой автоматического блокирования. Подтверждённый scope ограничен локальными
лабораторными и synthetic испытаниями.

## Ключевые свойства

- воспроизводимый pipeline от PCAP до evidence reconciliation;
- причинное 51-признаковое представление;
- frozen candidate с machine-readable identity;
- stateful processing на уровне episodes;
- versioned passive event contracts;
- durable at-least-once delivery;
- разделение scientific и runtime gates;
- immutable stage artifacts и evidence bundles;
- group-aware independent holdout methodology;
- blind commitments и external review package;
- fail-safe validators для manifests, paths, privacy и chronology.

## Архитектура

```text
Контролируемый трафик
→ PCAP
→ Zeek
→ causal feature window
→ frozen candidate
→ stateful decision
→ passive event
→ durable delivery
→ local verified sink
→ evidence reconciliation
```

PCAP обрабатывается Zeek, после чего feature builder формирует causal window.
Frozen candidate создаёт prediction, а stateful слой связывает observations в
episode и применяет замороженную policy. Passive event проходит versioned
contract и доставляется в локальный reference receiver.

Reference receiver подтверждает delivery protocol, но не является production
backend. Подробности приведены в
[архитектурном обзоре](docs/architecture/overview.md) и
[описании data flow](docs/architecture/data-flow.md).

## Проверенный scope

В пределах конкретных stage protocols подтверждены:

- локальные лабораторные сценарии;
- synthetic closed sets;
- causal feature extraction;
- frozen inference;
- stateful episode processing;
- passive event validation;
- local passive runtime;
- staging transport и durable receiver;
- длительная controlled local campaign;
- corrective timing и performance validation;
- external review protocol rehearsal;
- package builder и standalone verifier.

Каждое утверждение имеет ограничение и evidence reference в
[confirmed capabilities](docs/status/confirmed-capabilities.md).

## Что не подтверждено

Проект не подтверждает:

- accuracy на данных реальной организации;
- фактический external blind trial;
- production traffic capture;
- real shadow mode;
- backend или SIEM integration;
- production deployment;
- automatic enforcement;
- network blocking;
- реальные notifications;
- независимую external security/privacy validation.

Полный список запретов находится в
[prohibited capabilities](docs/status/prohibited-capabilities.md).

## Текущий frozen candidate

**Candidate ID:** `v03154:65a3dd912d845bc1`

Candidate создан в v0.3.15.4 на development corpus. Independent scientific
holdout выполнен в v0.3.15.5, а runtime-compatible event path подтверждён
последующими этапами.

Это development/research candidate. Его успешные лабораторные gates не означают
production readiness.

Machine-readable identity:

- [candidate registry](collectors/shadow/contracts/candidate_registry_v1.json);
- [candidate manifest](ml/artifacts/v0_3_15_4/candidate_manifest.json);
- [feature contract](ml/experiments/v0_3_15_4/feature_contract_v2.yaml);
- [event contract](collectors/shadow/contracts/shadow_event_v2.schema.json).

## Последние ключевые этапы

### v0.3.15.4

Контролируемая смешанная переработка сформировала current development candidate.
Результат разрешал только следующий independent holdout.

### v0.3.15.5

Independent scientific holdout прошёл predictive gates, но исходный runtime
event contract оказался несовместим. Candidate не был немедленно promoted.

### v0.3.15.5.1

Candidate-compatible event contract и prospective runtime recovery подтвердили
локальную runtime compatibility без backend или production claims.

### v0.3.16

Изолированный staging connector и reference receiver подтвердили durable
transport. Reference receiver остался проверочным sink, а не backend.

### v0.3.17

Валидная четырёхчасовая local campaign завершилась с отрицательным overall
policy result из-за evidence, timing, performance и corruption gates.

### v0.3.17.1

Corrective stage классифицировал historical findings, исправил evidence tooling
и прошёл targeted trial без изменения delivery path.

### v0.3.18

Подготовлены external review protocol, blind commitments, role separation,
deterministic evaluator, package builder и standalone verifier. Synthetic
rehearsal прошла, 40/40 negative scenarios отклонены.

Полная неизменённая хронология находится в
[version history](docs/status/version-history.md).

## Внешняя проверка

v0.3.18 подготовил процесс для будущей независимой проверки:

- frozen external review protocol;
- dataset, label, candidate, evaluator и prediction commitments;
- разделение ролей;
- blind label reveal;
- deterministic metric evaluation;
- package allowlist и manifest tree;
- standalone verification без Git, сети и backend;
- synthetic protocol rehearsal;
- 40/40 rejected negative scenarios.

В rehearsal использовался deterministic predictor, а не реальная модель.
Реальные внешние данные и labels не использовались:
`scientific_evidence=false`.

Подробнее: [external review package](docs/external_review/README.md).

## Структура репозитория

- `collectors/` — collectors, runtime adapters и passive event contracts;
- `datasets/` — tracked descriptions и metadata без raw datasets;
- `docs/` — текущая, исследовательская и историческая документация;
- `external_review/` — JSON Schemas external review contracts;
- `lab/` — локальные synthetic scenarios и isolation materials;
- `ml/` — feature code, candidate metadata, experiments и aggregate reports;
- `rehearsal/` — stage-specific runtime contracts и configuration;
- `runtime/` — generated local artifacts, исключённые из Git;
- `staging/` — изолированный transport, не являющийся backend;
- `backend/` — отдельный backend-код без current sensor integration;
- `tools/` — validators, builders и audit utilities.

Подробная карта: [repository layout](docs/getting-started/repository-layout.md).

## Быстрый старт

Проект не предоставляет одну команду для production-запуска всей системы.
Безопасный старт ограничен подготовкой окружения и проверками.

### Подготовка окружения

```powershell
python -m pip install -r ml/requirements.txt -r backend/requirements.txt
```

### Запуск тестов

```powershell
python -m pytest -q
```

### Проверка документации

```powershell
python tools/docs/validate_documentation.py --strict
python tools/docs/validate_project_status.py --strict
python tools/docs/validate_documentation_maintenance.py --strict
```

### Просмотр текущего статуса

Откройте [current status](docs/status/current-status.md) и
[`project-status.yaml`](docs/status/project-status.yaml).

Команды real capture, external trial и длительных runners намеренно не входят в
quick start. Руководство по проверкам:
[testing](docs/getting-started/testing.md).

## Документация

- [Навигационный индекс](docs/index.md)
- [Текущий статус](docs/status/current-status.md)
- [Архитектура](docs/architecture/overview.md)
- [Методология](docs/research/methodology.md)
- [Контракты](docs/contracts/index.md)
- [Протоколы](docs/protocols/index.md)
- [Итоговые отчёты](docs/reports/index.md)
- [Внешняя проверка](docs/external_review/README.md)
- [История этапов](docs/status/version-history.md)
- [Ограничения](docs/architecture/limitations.md)
- [Стиль и терминология](docs/contributing/documentation-style.md)

## Безопасность и ограничения

Испытания выполняются в локальной изоляции на synthetic fixtures. Current
runtime не имеет полномочий на automatic action, blocking или notification.
Backend integration и production connections запрещены.

Validators отклоняют unknown files, path traversal, commitment mismatch,
chronology violations и privacy/secret findings. Raw PCAP, model binaries,
labels, predictions, databases, WAL, journals и timing traces не добавляются в
Git.

## Воспроизводимость

Каждый завершённый stage сохраняет protocols, policy results, manifests,
detached hashes, test reports и claim-evidence ledgers. Historical artifacts не
переписываются для улучшения текущего narrative.

Если обнаружена ошибка, создаётся новая revision, corrective stage или
отдельное errata. Negative result остаётся доступным вместе с evidence.

Подробнее: [reproducibility](docs/research/reproducibility.md).

## Тестирование

Последний полный regression result зафиксирован при завершении v0.3.18:

- `1309 passed`;
- `0 failed`;
- `0 skipped`;
- `3 warnings`;
- compileall `6/6`.

Это исторический результат конкретного завершённого stage. Он не обновляется
автоматически после каждого commit.

## Статус и roadmap

v0.3.18 завершён с положительным design/rehearsal result. Разрешён только
v0.3.19: независимый review external package и согласование trial plan.

Фактический external trial потребует отдельного решения. Долгосрочная v0.4.x
ветка рассматривает evidence reconstruction и incident hypothesis layer, но не
является автоматическим следующим шагом или production-веткой.

См. [roadmap](docs/roadmap.md) и
[next stage](docs/status/next-stage.md).

## Лицензирование

Правовой режим распространения проекта пока не оформлен отдельной лицензией.
До появления `LICENSE` стандартные разрешения open-source лицензии не
заявляются.

# Приёмка runtime-целостности перед v0.3.8

## 1. Область проверки

После v0.3.7 и post-v0.3.7 аудита исправлен только будущий runtime pipeline и
выполнен короткий Docker smoke. Исторические datasets, candidates, predictions,
metrics и feature profiles v0.3.1–v0.3.7 не изменялись. Training, validation и
holdout v0.3.8 не выполнялись.

## 2. Исходное состояние репозитория

- исходный HEAD: `aef39efb4cf9877bc4aecc9d9f512e5f360a2d21`;
- исходная ветка: `main`, рабочее дерево было чистым и совпадало с `origin/main`;
- тег v0.3.7 указывал на `53773a9`;
- рабочая ветка: `fix/pre-v038-runtime-integrity`;
- `FILIN_SECURE_ARTIFACT_ROOT` отсутствовал.

## 3. Подтверждённые блокеры

### PRE-038-001 — повторные marker copies (критическая)

- Evidence: runtime отправлял 2/5 копий, resolver требовал ровно одну.
- Affected code: marker resolver, scenario executor, traffic-client, future builder.
- Historical impact: только limitation; исторические интервалы не пересчитаны.
- Correction: copy-aware last-start/first-end resolver и typed evidence hash.
- Verification: focused tests и final smoke с 2 start и 2 end copies во всех
  7 executions; отдельный failed attempt также подтвердил recovery при потере
  одной end copy и не был объявлен passed.
- Residual risk: tolerance должен задаваться будущим protocol и не маскировать overlap.

### PRE-038-002 — DNS отсутствовал в sensor capture (высокая)

- Evidence: BPF `not port 53`; Docker embedded resolver не виден на `eth0` даже
  после снятия фильтра.
- Affected code: future capture policy, traffic-client, Compose lab services.
- Historical impact: исторические PCAP не переписаны.
- Correction: future-only DNS capture и отдельный allowlisted internal UDP resolver.
- Verification: PCAP → Zeek `dns.log` → 3 assigned DNS events →
  `dns_query_count=3`: два успешных local names и локальный NXDOMAIN.
- Residual risk: resolver является узким лабораторным simulator, не production DNS.

### PRE-038-003 — netem не действовал во время run (критическая)

- Evidence: прежний controller выполнял rollback до experiment body.
- Affected code: environment controller и future scenario runner.
- Historical impact: v0.3.6/v0.3.7 condition claims не усилены задним числом.
- Correction: context manager с identity/network checks и rollback в `finally`.
- Verification: 7/7 applications и rollbacks; HTTP latency 2.190 ms без
  impairment против 81.180 ms при requested 40 ms + jitter.
- Residual risk: clients/background/proxy/TLS/topology остаются unsupported.

### PRE-038-004 — формальный no-fit audit (критическая)

- Evidence: прежний guard не оборачивал estimator во время prediction.
- Affected code: новый future-only predict entry point.
- Historical impact: исторические no-fit reports остаются ограниченными evidence.
- Correction: reachable-object runtime guard, static import/call audit, immutable
  artifact/prediction locks и no-predict resume.
- Verification: fit, fit_transform, partial_fit, calibration и tuning calls
  блокируются; normal predict и verified resume проходят.
- Residual risk: secure historical artifact не загружался для runtime проверки.

### PRE-038-005 — раздельный v0.6 contract (высокая)

- Evidence: schema/validator не знали future profile, builder не валидировал output.
- Affected code: feature dictionary, registry, schema, builder, validator.
- Historical impact: v0.3/v0.4/v0.5 не изменены.
- Correction: один machine-readable contract semantic version `0.6.0`, 20 features.
- Verification: 7-row smoke dataset прошёл exact-order validator и typed hashes.
- Residual risk: профиль проверен только на малом acceptance sample.

### PRE-038-006 — workflow fingerprints без runtime evidence (высокая)

- Evidence: WebSocket выполнял только handshake, роли и названия переутверждали
  фактическую семантику, terminal beacon создавал искусственную уникальность.
- Affected code: workflow catalog, traffic-client, audit tool.
- Historical impact: historical claims только документированы как limitations.
- Correction: реальные DNS/TCP/HTTP/WebSocket operations, честные approximation
  flags и collision report без provenance beacon.
- Verification: каждая из 6 semantic families дала assigned sensor events;
  WebSocket дал handshake, text/protocol pong, close и Zeek websocket event.
- Residual risk: 11 collision groups требуют объединения или переработки до campaign.

### PRE-038-007 — устаревший публичный статус (средняя)

- Evidence: `current-capabilities.md` называл v0.3.3 последним experiment.
- Affected code: documentation и validator.
- Historical impact: отсутствует.
- Correction: статус синхронизирован с `research-state.yaml`; validator охватывает
  current-capabilities, roadmap, experiments и development-history.
- Verification: strict documentation validation прошла.
- Residual risk: свободный текст всё равно требует review при следующих этапах.

## 4. Выполненные изменения

Реализованы семь исправлений выше, secure verifier, internal-only DNS simulator,
smoke runner и focused tests. Runtime artifacts остаются ignored. Исправленный
код нигде не описан как использованный в v0.3.1–v0.3.7.

## 5. Разрешение копий markers

Boundary выбирается как последний подтверждённый sensor start и первый sensor
end; при отсутствии полной sensor-пары используется согласованная control-пара.
Evidence содержит counts, first/last timestamps, spreads, source, reconciliation
и canonical hashes. Проверяются positive duration, nonce uniqueness, unknown
types, overlap и исключение marker flows. Smoke: 2/2 copies для каждого из 7
executions, все intervals положительны.

## 6. Проверка захвата DNS

Future capture разрешает DNS только при role `pre_training_smoke`, internal-only
policy, запрете external DNS и allowlist names. Запросы направлены к отдельному
`internal-dns:53/udp`, потому что embedded `127.0.0.11` не наблюдается на `eth0`.
Smoke получил 3 assigned Zeek DNS events и feature `dns_query_count=3`.

## 7. Жизненный цикл применения условий среды

Controller сохраняет qdisc before/during/after, requested и resolved parameters,
timestamps, measurement, commands и rollback result. Он проверяет Compose project
и network membership, не принимает host/shell identifiers. Assignment использует
только run identity и seed. Все 7 smoke executions выполнялись при активном netem;
7 rollback подтверждены.

## 8. Predict-only enforcement

Минимальный entry point не импортирует training/model-selection modules. Guard
активируется до `predict`, патчит training methods всех reachable objects и
fail-closed отклоняет неподдерживаемый объект. Lock содержит guarded classes,
blocked/attempted calls, entry point, artifact hashes before/after и prediction
hash. Resume проверяет lock и не загружает model.

## 9. Интеграция feature profile

`feature_dictionary.yaml` — источник ordered v0.6 contract. Для каждого feature
заданы formula, source fields, unit, range, missing/empty/zero-denominator policy.
Smoke hashes:

- feature schema: `8d9d305a5b59f7e9cfd711635e433ecbd6c293fbea0a0257b2ad650e53115135`;
- dataset: `bf49cb414990ed44d13f2a52f890da70f17eb4b5cf9f0ec875b718871a3d95a1`;
- row order: `8126c8bf17f6c1d283e42e5fffdf3b5f1a698d458a57cd3ab77598887df8c1a6`;
- execution mapping: `e5e637aa399198df77a456f136040a745a66f1dce4af8d67ce8018f2ceea390d`;
- marker intervals: `be3aa9d984fc7836641d239f053d6b8dd4e560bb327d41540438cbc2fde99872`.

## 10. Runtime evidence benign workflows

Smoke включал HTTP, DNS, WebSocket, TCP, mixed и safe attack-like families.
Assigned Zeek distributions различались по `conn`, `http`, `dns`, `files` и
`websocket`. Machine audit отдельно показывает actual protocol/target/operation,
unsupported claims и 11 observable collision groups; scenario-id beacon исключён
из основания сравнения. Final smoke нашёл 1 collision group по Zeek distribution
и 0 полностью идентичных feature vectors; рекомендация — объединять или
перерабатывать collision workflows до включения в training campaign.

## 11. Согласованность документации

Последний completed stage в документации — v0.3.7 с не пройденной policy.
Post-audit corrections помечены future-only. Backend integration, shadow mode и
production readiness остаются false. Исторические неточные v0.5 formulas
перечислены без ретроспективного пересчёта.

## 12. Проверка защищённых артефактов

Статус: `not_executed_secure_artifacts_unavailable`, `passed=false`.
Verifier unit tests проверили descriptor/manifest schemas, artifact/feature hashes,
model class, feature count, artifact type, traversal и symlink escape. Secure root,
artifact path и sensitive content не выводились.

## 13. Результаты unit tests

Strict documentation validation, release-image guard, repository artifact guard,
compileall, ML tests, backend tests и `git diff --check` выполнены. Итоговые числа
подтверждены последним run: 212 ML tests и 1 backend test, failures отсутствуют.

## 14. Результаты Docker smoke

Final attempt: `passed`, 7 executions, 7 validated rows, 7 non-empty independent
PCAP, 21/21 checks true. Evidence SHA-256:
`55d5fabf4dc49f9c65fcc257a6afb3c2293169c4fc83eff14692ca9f702812e4`.
Pre-existing containers остались running; smoke containers, networks и volumes
удалены. Диагностические attempts до final gate честно завершались failed на
journal permissions, relative CLI paths, marker tolerance и невидимом embedded
DNS; ни один из них не объявлен passed.

## 15. Невыполненные проверки

- full training/validation/holdout v0.3.8;
- historical v0.3.6/v0.3.7 predict, fit или tuning;
- verification реального secure artifact;
- production, backend и shadow-mode checks;
- полная runtime-кампания всех workflow IDs.

## 16. Защищённые артефакты, к которым не выполнялся доступ

Не читались secure frozen model binaries, закрытые historical datasets,
predictions и PCAP. Новые smoke PCAP/Zeek/events/dataset/report находились только
в ignored runtime storage и не добавляются в Git.

## 17. Оставшиеся риски

- secure artifact verification остаётся not executed до предоставления read-only root;
- smoke sample мал и не является статистической validation;
- 11 protocol collision groups и approximation workflows требуют design review;
- internal DNS и SSH являются лабораторными simulators;
- разрешение начать training не разрешает backend, shadow mode или deployment.

## 18. Решение о запуске обучения v0.3.8

`ready_for_v0_3_8_training`

Все обязательные runtime smoke checks выполнены и passed. Владелец может отдельной
командой начать новый training cycle v0.3.8 с новыми IDs/seeds/profile/policy.
Полная campaign в рамках этой приёмки не запускалась. Backend integration,
shadow mode и production deployment по-прежнему запрещены.

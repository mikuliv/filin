# Аудит исследовательской целостности после v0.3.7

## 1. Область аудита

Аудит рассматривает состояние репозитория после завершённого исследовательского
этапа v0.3.7. Сопоставлены документация, код, manifests, политики, тесты и
доступные локальные runtime-свидетельства. Исторические результаты v0.3.1–v0.3.7
неизменяемы: аудит не повторяет holdout prediction, не переобучает исторического
кандидата, не заменяет метрики и не меняет исторические feature profiles.

## 2. Состояние репозитория

- База аудита: `53773a991fd84d66cbe056979fe6182317a1ed03` в `main`.
- Последний завершённый этап: v0.3.7.
- Ветка аудита: `audit/post-v037-research-integrity`.
- Следующий свободный номер исследовательского этапа на момент аудита: v0.3.8.
  Сам аудит не запускает и не объявляет новый цикл обучения.

## 3. Граница защищённых артефактов

PCAP, datasets, нормализованные события, отчёты, predictions и model binaries
являются runtime-артефактами вне Git. Аудит использовал исходный код репозитория
и безопасные агрегированные чтения доступных локальных ignored datasets; строки
не выводились, защищённые файлы не копировались в отслеживаемые каталоги.
`FILIN_SECURE_ARTIFACT_ROOT` при первоначальном аудите не был настроен. Поэтому
проверки, которым необходим доверенный источник, имеют статус
`not_executed_secure_artifacts_unavailable`.

Frozen candidate manifest v0.3.7 уже отслеживался Git в исходном состоянии. Он
сохранён как неизменяемое историческое свидетельство. Будущие циклы должны
использовать внешнюю границу защищённых артефактов и добавлять в Git только
публичный descriptor без чувствительных данных.

## 4. Подтверждённые проблемы

### RI-001 — молчаливая длительность в одну секунду (критическая)

- Свидетельство: `build_network_sensor_v4_dataset.py` читает отсутствующее поле
  `actual_duration_seconds` и подставляет `1.0`. Записи исполнения содержат
  start/finish timestamps, но не заполняют это поле. Безопасная агрегированная
  проверка показала ровно одну секунду в 378/378 строках v0.3.4, 252/252 строках
  v0.3.6 и 1116/1116 строках v0.3.7 профиля v0.4.
- Затронутые версии: v0.3.4–v0.3.7.
- Исторические метрики изменены: нет.
- Влияние: нормализованные по времени rate features в этих исторических
  datasets не представляют marker-aligned sensor interval.
- Исправление: новый профиль для будущих циклов требует валидного marker
  interval, допускает проверенные actual timestamps только как вторичное
  свидетельство и не имеет числового fallback.
- Проверка: тесты marker duration, invalid duration, rate features и конечности
  model input.
- Остаточный риск: влияние на исторические метрики нельзя оценить без нового
  протокола и цикла обучения; старые holdouts запрещено повторно открывать как
  blind data.

### RI-002 — названия benign workflows не соответствуют поведению (высокая)

- Свидетельство: большинство идентификаторов `benign_*` v0.3.6/v0.3.7 попадали
  в catch-all ветку, выдающую одинаковую ограниченную последовательность GET.
- Затронутые версии: v0.3.6–v0.3.7.
- Исторические метрики изменены: нет.
- Влияние: заявленное разнообразие workflows превышает фактическое
  поведенческое разнообразие.
- Исправление: явные планы будущих workflows с различающимися HTTP, DNS, TCP и
  WebSocket actions и машиночитаемыми fingerprints.
- Проверка: тесты behavioral fingerprints, DNS observations и WebSocket.
- Остаточный риск: unit fixtures не заменяют изолированную runtime campaign.

### RI-003 — environment profiles оставались декларативными (высокая)

- Свидетельство: профили объявляют latency, jitter, loss, reordering и topology
  conditions, но campaign runner их не применяет; condition audit v0.3.7
  возвращал литеральные успешные значения.
- Затронутые версии: v0.3.6–v0.3.7.
- Исторические метрики изменены: нет.
- Влияние: заявления о condition independence и environment shift не имеют
  свидетельств фактического применения условий.
- Исправление: future-only controller для apply/verify/rollback с защитой,
  ограничивающей работу конкретным контейнером, и evidence records.
- Проверка: fake-executor тесты применения, проверки, независимости от label и
  отката.
- Остаточный риск: реальная проверка Docker/netem остаётся ручным локальным
  аудитом.

### RI-004 — неоднозначные хеши и утверждаемая целостность (высокая)

- Свидетельство: один holdout path вычисляет `marker_interval_sha256` от
  execution mapping, а не marker intervals; несколько полей PCAP/events имеют
  неоднозначную семантику; ряд результатов aggregation, condition, provenance и
  no-fit задавался литеральными booleans или нулевыми счётчиками вместо
  вычисляемых свидетельств.
- Затронутые версии: v0.3.5–v0.3.7.
- Исторические метрики изменены: нет.
- Влияние: исторические отчёты не подтверждают все заявленные свойства
  целостности.
- Исправление: типизированные canonical hashes, tri-state evidence и
  reproduction audit, независимо пересчитывающий агрегаты.
- Проверка: тесты hash domains, tri-state и обнаружения несовпадений
  reproduction.
- Остаточный риск: исправления исходного кода не доказывают свойства старых
  runs задним числом.

### RI-005 — integrity отсутствовала в итоговом gate (высокая)

- Свидетельство: v0.3.6 вычисляет `passed` только из metric/group/variant/
  stability checks, отдельно выводя константные integrity flags. Runners v0.3.5
  и v0.3.7 покрывали лишь часть своих YAML contracts.
- Затронутые версии: v0.3.5–v0.3.7.
- Исторические метрики изменены: нет.
- Исправление: generic policy evaluator для будущих циклов требует полного
  покрытия YAML, не считает `not_executed` успешным и проверяет zero recall для
  каждого поддерживаемого класса.
- Проверка: тесты policy coverage, пропущенных rules, tri-state и per-class
  recall.
- Остаточный риск: исторические policy outcomes сохраняются как исторические
  утверждения с перечисленными ограничениями.

### RI-006 — вводящие в заблуждение имена признаков (средняя)

- Свидетельство: `orig_resp_bytes_ratio` и `orig_resp_packets_ratio` вычисляют
  долю originator от общей величины, а не отношение originator к responder.
- Затронутые версии: профили v0.3.4–v0.3.7 на агрегации v0.4.
- Исторические метрики изменены: нет.
- Исправление: будущий профиль использует `orig_bytes_share` и
  `orig_packets_share` и публикует машиночитаемый словарь признаков.
- Проверка: formula/name contract и ordered-profile tests.
- Остаточный риск: исторические имена сохранены для воспроизводимости.

### RI-007 — противоречивый исследовательский статус (средняя)

- Свидетельство: README называл v0.3.3 последним этапом, а roadmap содержал
  дублированные и устаревшие блоки v0.3.3/v0.3.4 при наличии завершённого v0.3.7.
- Затронутые версии: документация на момент аудита.
- Исторические метрики изменены: нет.
- Исправление: `docs/research-state.yaml` стал авторитетным источником статуса,
  validator проверяет ключевые текстовые утверждения.
- Проверка: тесты согласованности документации и CI validator.
- Остаточный риск: свободный текст вне валидируемых утверждений по-прежнему
  требует рецензирования.

## 5. Неподтверждённые проблемы

- Не найдено свидетельств, что Git отслеживает PCAP, datasets, predictions,
  reports или model binaries.
- Реальное вычисление PCAP SHA-256 уже присутствовало в sensor storage/preflight
  и старом environment runner. Проблемой являлось непоследовательное применение
  и неоднозначные downstream-названия, а не полное отсутствие PCAP hashing.
- Аудит не выполнял исторический holdout prediction или model fit.

## 6. Проверки, заблокированные отсутствием защищённых артефактов

- Проверка frozen candidate binary по внешнему manifest.
- Воспроизведение PCAP → normalized events для всех исторических runs.
- Полное воспроизведение Zeek output и marker interval hashes.
- Сквозное сравнение агрегации из защищённых normalized events.

Эти проверки не являются ни успешными, ни проваленными. До предоставления
владельцем доверенного read-only `FILIN_SECURE_ARTIFACT_ROOT` их статус —
`not_executed_secure_artifacts_unavailable`.

## 7. Оценка влияния на исторические результаты

Отчёты v0.3.4–v0.3.7 остаются записью результатов исторического кода, а не
утверждением об исправленной семантике. Дефект duration напрямую влияет на
интерпретацию rate features. Дефекты workflows и conditions ослабляют заявления
о разнообразии и независимости. Константные integrity evidence ослабляют
заявления о воспроизводимости. Ни одно из этих ограничений не разрешает замену
метрик задним числом. Исправленная семантика требует нового feature profile,
новых training data, нового candidate, новой internal validation и действительно
нового prospective holdout.

## 8. Выполненные изменения

Реализованы исправления только для будущих циклов:

- строгий resolver marker intervals и привязка evidence без fallback в одну
  секунду;
- `network_sensor_v0_6_integrity`, исправленные имена share-признаков, точный
  ordered contract и машиночитаемый feature dictionary;
- явные ограниченные локальные benign workflows, включая DNS observations и
  реальный WebSocket upgrade endpoint;
- container-scoped controller netem apply/verify/rollback и вычисляемый condition
  evidence audit;
- семантически разделённые hash domains, tri-state integrity evidence и
  независимый comparator агрегации;
- внешний secure-artifact descriptor и безопасный verifier через
  `FILIN_SECURE_ARTIFACT_ROOT`;
- generic YAML policy evaluator с полным покрытием, integrity и zero-recall gate
  для каждого поддерживаемого класса;
- авторитетный `docs/research-state.yaml`, синхронизированные README/status/
  roadmap и validator документации;
- исключение protected/generated artifacts, versioned container image tags,
  расширенные CI и unit tests.

Ни один исторический dataset, report, prediction, candidate, metric, tag или
feature profile не был заменён. Исторический condition audit v0.3.7 теперь
сообщает `not_executed` при отсутствии application evidence вместо литерального
успеха.

## 9. Выполненные тесты

- Validator документации: пройден.
- Guard изменяемых image tags: пройден после закрепления версий.
- Проверка исключения protected/generated artifacts: пройдена.
- `compileall` для tools, ML, backend и лабораторного кода: пройден.
- Полный ML unit discovery: 181 тест пройден.
- Полный backend unit discovery: 1 тест пройден.
- Новые focused tests покрывают duration, marker evidence, конечность feature
  projection, feature dictionary, workflow fingerprints, DNS/WebSocket,
  применение и откат условий среды, hash domains, tri-state integrity,
  aggregation reproduction, отсутствие secure root, policy coverage, per-class
  zero recall, research state и artifact exclusion.
- `git diff --check`: пройден.

## 10. Невыполненные тесты

Protected runtime audits и длительная Docker campaign намеренно исключены из
автоматического CI и не выполняются без доверенного secure-artifact root. Не
выполнены: проверка hash внешнего frozen artifact, реальное воспроизведение
PCAP/Zeek/normalized events, полное воспроизведение исторической агрегации и
реальное применение Docker/netem. Их статусы —
`not_executed_secure_artifacts_unavailable` или `not_executed_runtime_manual`, а
не passed.

## 11. Оставшиеся риски

- Утверждаемые поля исторических отчётов нельзя задним числом превратить в
  вычисленные свидетельства.
- Lock v0.3.6 хранит одинаковые значения для PCAP и normalized-event hash и
  использует execution-mapping hash как marker-interval hash. Эти поля остаются
  историческим свидетельством дефекта, а не валидным типизированным hash proof.
- Тест environment controller с fixture не доказывает возможности host kernel
  или Docker.
- Исторический tracked frozen manifest v0.3.7 остаётся исключением из будущей
  политики внешних manifests.
- Version tags снижают риск `latest`, но не являются registry digests; перед
  release всё ещё нужны digest pinning и проверка SBOM/licenses.

## 12. Требования к следующему циклу обучения

Использовать новые scenario/run IDs, seeds и versioned profile; захватывать
валидные marker intervals; применять и откатывать зарегистрированные conditions;
построить новый dataset; обучить нового кандидата без настройки по holdouts
v0.3.6/v0.3.7; заморозить artifact, schema, policy и integrity evidence до
валидации; требовать полного policy coverage и отсутствия zero-recall среди
поддерживаемых классов.

## 13. Требования к следующему перспективному holdout

После заморозки candidate использовать ранее не применявшиеся, заранее
зарегистрированные catalog и protocol. До единственного prediction pass
зафиксировать source hashes, row order и execution mapping. Запретить fit,
calibration, threshold tuning, feature selection, row exclusion, metric-driven
reruns и повторный predict при resume. Хранить артефакты в secure root и
публиковать только нечувствительные агрегированные свидетельства.

# Приёмка runtime-целостности перед v0.3.8

## 1. Область проверки

Проверка выполняется после завершения v0.3.7 и post-v0.3.7 аудита. Цель —
устранить блокеры только будущего pipeline и выполнить короткий Docker smoke,
не являющийся training, validation или holdout. Исторические результаты,
кандидаты, predictions и feature profiles v0.3.1–v0.3.7 неизменяемы.

## 2. Исходное состояние репозитория

- Исходный HEAD: `aef39efb4cf9877bc4aecc9d9f512e5f360a2d21`.
- Исходная ветка: `main`, рабочее дерево чистое.
- `main` совпадал с `origin/main`.
- Исторический тег v0.3.7 указывает на `53773a9`.
- Ветка исправлений: `fix/pre-v038-runtime-integrity`.
- `FILIN_SECURE_ARTIFACT_ROOT` не настроен.

## 3. Подтверждённые блокеры

### PRE-038-001 — marker copies несовместимы с resolver (критическая)

- Свидетельство: runtime отправляет 2/5 копий, resolver требует ровно одну.
- Затронутый код: `scenario_executor.py`, traffic-client `send_marker()`,
  `marker_intervals.py`, future dataset builder.
- Историческое влияние: результаты не меняются; дефект ограничивает будущий
  pipeline.
- Исправление: детерминированный copy-aware resolver и canonical evidence.
- Проверка: unit tests и Docker smoke с несколькими копиями.
- Остаточный риск: фиксируется после smoke.

### PRE-038-002 — DNS исключён из PCAP (высокая)

- Свидетельство: execution capture и sidecar используют `not port 53`.
- Затронутый код: `scenario_executor.py`, Docker compose capture command.
- Историческое влияние: исторические PCAP не переписываются.
- Исправление: future-only capture без фильтра DNS при internal-only network.
- Проверка: DNS → PCAP → Zeek dns.log → normalized event → feature.
- Остаточный риск: фиксируется после smoke.

### PRE-038-003 — netem не действует во время run (критическая)

- Свидетельство: controller выполняет apply/verify/rollback одним вызовом до
  любого experiment body и не подключён к runner.
- Историческое влияние: подтверждает ограничение v0.3.6/v0.3.7, метрики не
  меняются.
- Исправление: context manager с rollback в `finally` и future runner wiring.
- Проверка: unit tests и измерение latency в Docker smoke.
- Остаточный риск: фиксируется после smoke.

### PRE-038-004 — no-fit guard не охватывает prediction (критическая)

- Свидетельство: отдельный `NoFitGuard` создаётся после prediction и только
  печатает нулевые counters.
- Историческое влияние: исторический audit остаётся ограниченным свидетельством.
- Исправление: отдельный predict-only process с активным запретом training APIs.
- Проверка: focused tests запрещённых вызовов, hash и resume.
- Остаточный риск: фиксируется после реализации.

### PRE-038-005 — v0.6 profile не подключён к registry (высокая)

- Свидетельство: профиль находится в отдельном модуле; `schema.py` и validators
  его не знают; builder не запускает validator.
- Историческое влияние: v0.3/v0.4/v0.5 не меняются.
- Исправление: единый registry/contract, строгий validator и builder evidence.
- Проверка: exact order, metadata/X separation, ranges и hashes.
- Остаточный риск: фиксируется после smoke dataset.

### PRE-038-006 — benign fingerprints не являются runtime evidence (высокая)

- Свидетельство: WebSocket выполняет только handshake; часть уникальности
  создаётся metadata POST; названия ряда симуляций сильнее фактической семантики.
- Историческое влияние: исторические claims получают limitation, результаты не
  меняются.
- Исправление: честный simulation catalog, реальные WebSocket frames, target
  roles и collision audit.
- Проверка: PCAP/Zeek/feature-family smoke evidence.
- Остаточный риск: не каждый workflow будет включён в короткий smoke.

### PRE-038-007 — документация противоречит research state (средняя)

- Свидетельство: `current-capabilities.md` называет v0.3.3 последним этапом.
- Историческое влияние: отсутствует.
- Исправление: синхронизация и расширенный validator.
- Проверка: documentation tests.
- Остаточный риск: свободный текст требует рецензирования.

## 4. Выполненные изменения

Заполняется по мере реализации. Все изменения относятся только к будущему
циклу и pre-v0.3.8 smoke.

## 5. Разрешение копий markers

Ожидает реализации и runtime-проверки.

## 6. Проверка захвата DNS

Ожидает Docker smoke.

## 7. Жизненный цикл применения условий среды

Ожидает реализации и Docker smoke.

## 8. Predict-only enforcement

Ожидает реализации.

## 9. Интеграция feature profile

Ожидает реализации и smoke dataset.

## 10. Runtime evidence benign workflows

Ожидает реализации и Docker smoke.

## 11. Согласованность документации

Ожидает синхронизации.

## 12. Проверка защищённых артефактов

Secure root недоступен. Runtime artifact verification имеет статус
`not_executed_secure_artifacts_unavailable`, а не passed.

## 13. Результаты unit tests

Ожидают выполнения.

## 14. Результаты Docker smoke

Ожидают выполнения. До успешного прохождения решение не может быть ready.

## 15. Невыполненные проверки

- Полная training campaign v0.3.8 запрещена и не будет выполняться.
- Исторические holdout predictions не выполняются.
- Проверки доверенного secure root не выполняются до его предоставления.

## 16. Защищённые артефакты, к которым не выполнялся доступ

Frozen model binaries, исторические PCAP, predictions и закрытые datasets не
читаются и не копируются в Git.

## 17. Оставшиеся риски

Заполняются после unit и Docker smoke acceptance.

## 18. Решение о запуске обучения v0.3.8

`not_ready_for_v0_3_8_training`

Решение может измениться только после успешного прохождения всех обязательных
unit и runtime smoke checks. Это решение не разрешает backend integration,
shadow mode или production deployment.

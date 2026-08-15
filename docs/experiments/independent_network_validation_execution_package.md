# Готовность execution package независимой сетевой валидации

## Статус

`EXECUTION_PACKAGE_BLOCKED_BY_FREEZE_GAP`.

Официальный pre-experiment freeze `network-validation-d6e946188d870a7f` валиден и неизменён. Его canonical digest — `870946390f9ca8a5fe0ac2c53e7855e979ef242d9486815ef67d6d47ca9cbe41`, source Git SHA — `a6a979aef803ba776933b39dbd7607bd0833cc63`, содержащий freeze commit — `a955ce3fdb1387266a9f1eb21a6e4db6b0a3eed8`.

Freeze достаточен для фиксации факторной матрицы, но недостаточен для однозначного исполнения кампании. Исполняемый candidate и run plan не созданы. Научная кампания не запускалась, корпус и метки не создавались, модель не обучалась, predictions и научные метрики не рассчитывались. Следующее допустимое действие — superseding-freeze review без запуска кампании.

## Аудит полноты

| Execution-affecting field | Frozen | Source | Scientific significance | Required before execution |
| --- | --- | --- | --- | --- |
| Scenario definitions | да | `campaign_matrix_digest` | семантика трафика | нет |
| Scenario template count | да | `seal_preconditions.scenario_count` | покрытие матрицы | нет |
| Generator family | да | `campaign_matrix_digest` | разнообразие генераторов | нет |
| Infrastructure profile | да | `campaign_matrix_digest` | разнообразие инфраструктуры | нет |
| Target implementation | да | `campaign_matrix_digest` | разнообразие целей | нет |
| Intensity | да | `campaign_matrix_digest` | распределение нагрузки | нет |
| Background policy | да | `campaign_matrix_digest` | фоновой трафик | нет |
| Scenario parameter vectors | да | `campaign_matrix_digest` | реализация сценария | нет |
| Scientific seed values | да | `campaign_matrix_digest` | воспроизводимость действий | нет |
| Session tokens | да | `campaign_matrix_digest` | группировка сессий | нет |
| Counterfactual pairs | да | `counterfactual_plan_digest` | контроль proxy-факторов | нет |
| Feature contract and order | да | `feature_contract_digest`, `feature_order_digest` | вход модели | нет |
| Acceptance criteria | да | `acceptance_criteria_digest` | правила решения | нет |
| Image identities | да | `image_lock_digest` | воспроизводимость среды | нет |
| Scenario action retry | да | `campaign_matrix_digest` | сетевое поведение | нет |
| Scenario timeouts | да | `campaign_matrix_digest` | сетевое поведение | нет |
| Scientific repetition policy | нет | отсутствует | размер выборки и дисперсия | да |
| Execution order policy | нет | отсутствует | carry-over и временное смещение | да |
| Execution concurrency policy | нет | отсутствует | contention и перекрёстный трафик | да |
| Session isolation/reset policy | нет | отсутствует | перенос состояния между сессиями | да |
| Warmup/cooldown policy | нет | отсутствует | загрязнение границ | да |
| Capture start lead/stop lag | нет | отсутствует | полнота захвата | да |
| Clock offset tolerance | нет | отсутствует | совмещение событий и меток | да |
| Campaign retry/replacement policy | нет | отсутствует | selection bias | да |
| Exclusion reason allowlist | нет | задана только максимальная доля | selection bias | да |
| Exact split assignments | нет | есть policy без assignments | blind evaluation и leakage | да |
| Output/session integrity schema | нет | есть только частичные runtime-структуры | полнота и проверяемость корпуса | да |

Порядок строк в замороженной матрице не считается порядком исполнения: freeze не объявляет такую семантику, а длительно живущие client/target процессы не имеют зафиксированного межсессионного reset-контракта. Значения seeds 1000–1071 зафиксированы digest матрицы, но количество применений каждой строки не задано.

## Контракты и архитектура

Readiness-код находится в `lab/network_validation/execution_package.py`. Структурные контракты находятся в `lab/network_validation/execution/`:

- `label_vault_contract.json` задаёт исходное состояние `absent_locked`, условия будущего unlock и границу runner/evaluator;
- `output_contract.json` перечисляет будущие session outputs, обязательные digests и запрещает результаты обучения и оценки на фазе сбора;
- `campaign_ledger_contract.json` задаёт append-only audit trail; allowlist причин retry и exclusion намеренно пусты до superseding freeze;
- `preflight_contract.json` задаёт fail-closed проверки и текущий `execution_allowed: false`.

Технические идентификаторы, локальные пути и timestamps не входят в scientific identity preview. Preview детерминированно связывает официальный freeze и digests контрактов, но не является execution-package candidate, не содержит run plan и не разрешает исполнение.

Будущая последовательность разделена на три фазы:

1. Data Collection: runner видит сценарную семантику; PCAP, Zeek logs и features создаются без labels.
2. Training / Calibration: используются только заранее назначенные train/calibration splits; final holdout остаётся закрыт.
3. Blinded Evaluation: frozen model создаёт predictions до разрешённого label unlock и расчёта metrics.

Evaluator до unlock получает только feature row, значения 51 признака, digests feature contract/order и session integrity. Ему запрещены behavior, generator family, infrastructure, target, scenario/session tokens, seed, split assignment, marker и path metadata.

## Run plan, retry и exclusion

Матрица сохраняет 72 уникальных scenario templates, 72 уникальных текущих session tokens, шесть behaviors, две generator families, две infrastructure profiles, две target implementations, два порта, три intensity bands и 24 counterfactual pairs. Число execution sessions равно нулю, потому что repetition policy отсутствует. Split не материализован.

Per-action retry и timeout входят в строки сценариев и описывают наблюдаемое сетевое поведение. Они не заменяют отсутствующие правила повтора или замены неуспешной сессии. До superseding freeze запрещены автоматические retry, replacement, row exclusion и scenario substitution. Любая будущая операция должна иметь заранее разрешённый reason code и append-only запись.

## Preflight

До исполнения должны пройти integrity-проверки official freeze, source/containing commits, матрицы, counterfactual plan, acceptance criteria, feature contract/order и image lock. Дополнительно требуются полный execution policy, закрытый label vault, новый или пустой output root, чистое дерево и SHA коммита execution tooling.

Текущий preflight всегда возвращает `execution_allowed: false`. Устранение gaps требует отдельного superseding freeze; исправлять существующий immutable artifact на месте нельзя.

## Безопасные команды

```powershell
python -m lab.network_validation.cli audit-execution-readiness
python -m lab.network_validation.cli build-execution-package-preview
python -m lab.network_validation.cli validate-execution-package
python -m lab.network_validation.cli inspect-run-plan
python -m lab.network_validation.cli inspect-label-boundary
```

Команды выполняют только чтение и валидацию. Они не запускают контейнеры, capture, Zeek, модель или научную кампанию и не создают runtime-артефакты.

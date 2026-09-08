# Инфраструктура независимой сетевой проверки

Каталог содержит технический контур Phase 1: контракты, план, генераторы, сервисы Docker, обработку PCAP и Zeek, построение 51 признака, ослепление, сопоставление и проверки готовности. Он не содержит научного корпуса и сам по себе не доказывает качество модели.

## Текущее состояние

Последний официальный файл — `execution/official_execution_package_v4.json`: 288 шаблонов, 864 единицы, три повтора, 24 контрфактуальные пары и 51 признак. В пакете указаны `scientific_campaign_started=false` и 0 научных сессий. Текущий код после выпуска v4 исправляет запуск Zeek (`/usr/local/zeek/bin/zeek` через `bash -c`), поэтому перед научной работой требуется новый официальный заменяющий пакет.

## Сетевой путь

```text
поведение → общий клиент → изолированная сеть Docker → цель
→ захват → PCAP → Zeek → временные журналы → 51 призна́к
```

Семейства `family_a` и `family_b`, профили `profile_a` и `profile_b`, цели `target_a` и `target_b`, порты `8080` и `9080` проверяются независимо. Поведения: `navigation`, `credential_rejection`, `periodic_callback`, `throttled_pressure`, `service_discovery`, `path_inspection`. Каждому шаблону назначается один режим фоновой активности — `http`, `dns`, `keepalive` или `combined`; каждый режим распределён по 72 шаблона. Фон не является дополнительным фактором.

## Контракты и предохранители

- `contracts.py` проверяет сценарии, события, marker и манифест захвата;
- `parameter_verification.py` сравнивает заданные параметры с наблюдениями Zeek;
- `feature_adapter.py` изолирует состояние по сессии и сохраняет порядок признаков;
- `causal_guard.py` допускает только точный конечный числовой вектор из 51 полей;
- `planning.py` проверяет пары, разбиение целыми сессиями и риски proxy;
- контракт среды выполнения задаёт предварительную проверку, сопоставление, повторы, журнал, запечатывание и восстановление;
- `candidate_identity.py` связывает внутренний и внешний идентификатор по SHA-256.

Сырые PCAP и журналы Zeek не редактируются. Marker исключается только во временной копии входа модели; DNS не меняется. Смешанный marker/scenario UID даёт `processing_integrity_failure`. Полное описание: [актуальная методика](../../docs/research/independent-network-validation.md).

## Безопасные команды

Ниже перечислены только команды статической проверки, чтения контрактов и построения предпросмотра. Они не создают научный корпус:

```powershell
python -m lab.network_validation.cli --help
python -m lab.network_validation.cli validate-config
python -m lab.network_validation.cli plan-campaign
python -m lab.network_validation.cli validate-counterfactuals
python -m lab.network_validation.cli validate-split
python -m lab.network_validation.cli inspect-phase1-runtime-contract
python -m lab.network_validation.cli audit-initialization-contract
python -m lab.network_validation.cli inspect-ledger-contract
python -m lab.network_validation.cli inspect-mapping-contract
python -m lab.network_validation.cli inspect-label-boundary
python -m lab.network_validation.cli inspect-run-plan
python -m lab.network_validation.cli validate-runtime-execution-package
python -m lab.network_validation.cli audit-execution-preflight --help
```

`render-compose`, `inspect-environment`, `validate-parameter-contract` и `validate-capture-manifest` требуют осознанно подготовленных входов; их не следует запускать на неизвестных данных.

## Опасные команды

`run-one-phase1-session` запускает научное поведение, создаёт PCAP, журналы, запись сопоставления и запись журнала. `preflight-phase1-session` проверяет среду, но требует внешний каталог секретов. `recover-phase1-sealed-completion` изменяет журнал завершения. `run-technical-smoke` и `run-factor-orthogonality-smoke` создают сетевые временные данные. Они не являются безопасными примерами и требуют отдельного явного разрешения, согласованных каталогов и проверки актуального заменяющего пакета. Для исторического v4 две попытки уже исчерпаны, поэтому его предварительная проверка и третья попытка запрещены; команда относится только к будущему заменяющему пакету после новой инициализации.

Команды создания официального пакета или его фиксации также изменяют зафиксированные операционные материалы и выполняются только владельцем процесса. Научный запуск, создание меток, раскрытие сопоставления, обучение модели, прогнозы и метрики в документации намеренно не выдаются как готовый сценарий.

## Тестирование

```powershell
python -m pytest ml/tests/test_network_validation_infrastructure.py -q
python -m pytest ml/tests/test_network_validation_phase1_runtime.py -q
docker compose -f lab/network_validation/compose.yaml config
```

Контракт признаков — `ml/experiments/v0_3_15_4/feature_contract_v2.yaml`, критерии — `config/acceptance_criteria.json`, образ — `config/image_lock.json`, план — `execution/phase1_run_plan.json`, контракт среды выполнения — `execution/phase1_runtime_contract.json`. Зависимости сетевой проверки перечислены в `requirements.lock`; клиент и цели используют стандартную библиотеку Python внутри образов.

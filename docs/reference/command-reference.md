# Справочник команд

Все команды выполняются из корня репозитория. Команды ниже разделены по риску: чтение и проверка не создают научный корпус; операции Phase 1 требуют отдельного допуска.

## Проверки документации и кода

```powershell
python -m tools.docs.validate_documentation_v2 --strict
python -m tools.docs.validate_documentation_freshness --strict
python -m tools.docs.validate_documentation_authority
python -m tools.docs.validate_documentation_links
python -m tools.docs.validate_documentation_immutability
python -m tools.docs.validate_documentation_terminology
python -m tools.docs.validate_russian_narrative --strict
python -m compileall backend collectors incident_reconstruction lab lab_console ml rehearsal staging tools
```

Инвентаризация выполняется после правок:

```powershell
python -m tools.docs.build_documentation_inventory
```

Перед коммитом проверьте `git diff --check`. Инвентаризация и защищённый список являются производными представлениями; содержимое защищённых источников не переписывается.

## Безопасный CLI сетевой проверки

```powershell
python -m lab.network_validation.cli --help
python -m lab.network_validation.cli validate-config
python -m lab.network_validation.cli plan-campaign
python -m lab.network_validation.cli validate-counterfactuals
python -m lab.network_validation.cli validate-split
python -m lab.network_validation.cli inspect-phase1-runtime-contract
python -m lab.network_validation.cli inspect-run-plan
python -m lab.network_validation.cli inspect-label-boundary
python -m lab.network_validation.cli inspect-ledger-contract
python -m lab.network_validation.cli inspect-mapping-contract
python -m lab.network_validation.cli audit-initialization-contract
python -m lab.network_validation.cli validate-runtime-execution-package
python -m lab.network_validation.cli audit-execution-preflight --help
```

Эти команды читают конфигурацию или показывают контракт. Они не создают scientific session, PCAP, labels, predictions или метрики. Команды предпросмотра, materialize и создания официального пакета могут изменять операционные артефакты и запускаются только владельцем процесса.

## Лабораторная консоль

```powershell
$env:FILIN_CONSOLE_TOKEN = "локальный-одноразовый-токен"
python -m lab_console --host 127.0.0.1 --port 8043
```

Консоль слушает только localhost, записывает изменяемый слой в `runtime/lab_console/` и не является серверной интеграцией. Проверки цикла:

```powershell
python -m tools.lab_console.verify_console
python -m tools.lab_console.verify_v044
python -m tools.lab_console.verify_v045
python -m tools.lab_console.verify_v046
python -m tools.lab_console.verify_v047
```

## Запрещённый без отдельного допуска запуск

`run-one-phase1-session` запускает научную единицу и создаёт PCAP, журналы Zeek, mapping и записи журнала. `preflight-phase1-session` требует защищённое секретное хранилище. `recover-phase1-sealed-completion` изменяет состояние завершения. `run-technical-smoke` и `run-factor-orthogonality-smoke` создают сетевые временные данные. Не копируйте эти операции в обычную проверку и не направляйте результаты в tracked repository.

## Как читать результат

Успешная команда подтверждает только свой контракт. Она не означает внешнюю валидность, истинность гипотезы, научный pass, промышленную эксплуатацию readiness, право регистрации кандидата или разрешение автоматического ответа. Фактические числа регрессии фиксируются в отчёте конкретного окружения; baseline описан в [тестировании](../getting-started/testing.md).

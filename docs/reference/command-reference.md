# Справочник команд

Все команды запускаются из корня репозитория. Перечень сетевых команд ниже синхронизирован с `lab/network_validation/cli.py`: в текущем парсере 42 команды. Если код и этот документ расходятся, сначала проверяйте сам парсер и обновляйте справочник.

## Проверки документации и кода

```powershell
python -m tools.docs.validate_documentation_v2 --strict
python -m tools.docs.validate_documentation_freshness --strict
python -m tools.docs.validate_documentation_authority
python -m tools.docs.validate_documentation_links
python -m tools.docs.validate_documentation_immutability
python -m tools.docs.validate_documentation_terminology
python -m tools.docs.validate_russian_narrative --strict
python -m tools.docs.validate_documentation_identifiers --strict
python -m tools.docs.validate_documentation_cli --strict
python -m compileall backend collectors incident_reconstruction lab lab_console ml rehearsal staging tools
```

После правок обновляйте производные описи командой `python -m tools.docs.build_documentation_inventory`, а затем проверяйте `git diff --check`. Генератор индексов запускается командой `python -m tools.docs.build_documentation_indexes`. Эти операции не запускают научные сессии.

## Сетевой CLI: только чтение и валидация

В этой группе команды читают конфигурацию, план, контракты и уже существующие артефакты. Они не создают научные сессии, PCAP, метки, предсказания или метрики. Общий флаг `--json` указывается перед подкомандой. Если ниже аргументы не перечислены, дополнительных аргументов у команды нет. Аргументы с путями необязательны, кроме явно обозначенных обязательными.

| Команда | Назначение и аргументы | Состояние и безопасность |
|---|---|---|
| `validate-config` | Проверка основной конфигурации; `--campaign` | Только чтение |
| `plan-campaign` | Построение и проверка плана; `--campaign` | Только чтение |
| `validate-counterfactuals` | Проверка контрфактуальных пар; `--campaign` | Только чтение |
| `validate-split` | Проверка разбиения по повторам; `--campaign` | Только чтение |
| `validate-freeze-candidate` | Проверка кандидата freeze; `--campaign` | Только чтение |
| `inspect-proxy-risks` | Просмотр рисков прокси-признаков; `--campaign` | Только чтение |
| `inspect-image-lock` | Просмотр блокировки образов; `--image-lock` | Только чтение |
| `verify-image-reproducibility` | Сравнение двух образов; обязательные `--left` и `--right` | Только чтение |
| `validate-official-freeze` | Проверка официального freeze; `--campaign`, `--acceptance-criteria`, `--image-lock`, `--freeze` | Только чтение |
| `audit-execution-readiness` | Аудит готовности выполнения; те же четыре аргумента, что у официального freeze | Только чтение |
| `audit-execution-preflight` | Аудит предварительных условий пакета; `--package` | Только чтение |
| `validate-execution-package` | Проверка пакета; `--package`, `--campaign`, `--acceptance-criteria`, `--image-lock`, `--freeze` | Только чтение |
| `validate-superseding-inputs` | Проверка входов заменяющего пакета | Только чтение |
| `validate-official-superseding-freeze` | Проверка заменяющего freeze; `--freeze` | Только чтение |
| `validate-superseding-execution-package` | Проверка заменяющего пакета; `--package` | Только чтение |
| `audit-initialization-contract` | Проверка контракта инициализации | Только чтение |
| `inspect-ledger-contract` | Просмотр общего контракта журнала кампании | Только чтение |
| `inspect-mapping-contract` | Просмотр контракта сопоставления | Только чтение |
| `inspect-phase1-runtime-contract` | Просмотр профиля событий Phase 1, полей и переходов | Только чтение |
| `inspect-run-plan` | Просмотр плана выполнения; парсер принимает `--campaign`, `--acceptance-criteria`, `--image-lock`, `--freeze`, но обработчик читает закреплённый план | Только чтение |
| `inspect-label-boundary` | Проверка границы между оценщиком и скрытой разметкой | Только чтение |
| `inspect-environment` | Просмотр локальной среды выполнения | Только чтение |
| `render-compose` | Рендеринг конфигурации Compose | Только чтение |
| `validate-parameter-contract` | Проверка одного сценария; обязательные `--scenario` и `--zeek-dir` | Только чтение |
| `validate-capture-manifest` | Проверка манифеста захвата; обязательные `--manifest`, `--dataset-root`, `--executions`, необязательный `--markers` | Только чтение |

## Предпросмотр и операции с пакетами

Эти команды относятся к операционному контуру. Предпросмотр обычно читает входы и формирует результат для проверки, а `materialize` и `create-official-*` могут записать операционные или официальные артефакты. Они не должны считаться научным стартом, но требуют проверки пути вывода и исходных commit, а также разрешения владельца.

| Команда | Назначение и аргументы | Побочный эффект |
|---|---|---|
| `build-freeze-preview` | Предпросмотр freeze; `--campaign`, `--acceptance-criteria`, `--image-lock` | Только чтение; результат выводится в консоль |
| `create-official-freeze` | Создание официального freeze; те же пути плюс `--output`, подтверждение `--confirm-official-freeze` | Запись официального артефакта |
| `build-execution-package-preview` | Предпросмотр пакета; парсер принимает `--campaign`, `--acceptance-criteria`, `--image-lock`, `--freeze`, обработчик использует закреплённые входы | Только чтение; результат выводится в консоль |
| `materialize-execution-package-inputs` | Материализация входов пакета | Запись операционных входов |
| `create-official-execution-package` | Создание официального пакета; `--output`, `--confirm-official-package` | Запись официального пакета |
| `materialize-superseding-inputs` | Материализация входов заменяющего пакета | Запись операционных входов |
| `build-superseding-execution-package-preview` | Предпросмотр заменяющего пакета; необязательный `--operational-contracts-commit` | Только чтение; результат выводится в консоль |
| `create-official-superseding-freeze` | Создание заменяющего freeze; `--output`, `--confirm-official-freeze` | Запись официального freeze |
| `create-official-superseding-execution-package` | Создание заменяющего пакета; `--output`, `--operational-contracts-commit`, `--confirm-official-package` | Запись официального пакета |
| `build-runtime-execution-package-preview` | Предпросмотр пакета среды выполнения; необязательный `--runtime-sources-commit` | Только чтение; результат выводится в консоль |
| `validate-runtime-execution-package` | Проверка пакета среды выполнения; `--package` | Только чтение |
| `create-official-runtime-execution-package` | Создание пакета среды выполнения; `--output`, `--runtime-sources-commit`, `--confirm-official-package` | Запись официального пакета |

Пакет, фиксация, исходный коммит, сопоставление и состояние инициализации должны быть проверены как единое целое. В рамках обычной документационной работы эти команды не запускаются.

## Научная сессия и диагностические тесты

Следующие команды не являются безопасными примерами. Для них нужны отдельные каталоги, секретное хранилище и явное разрешение:

> **`run-one-phase1-session` выполняет научный сеанс.** Не используйте её как обычную диагностику. Необходимы соответствующий официальный пакет, инициализация, успешная предварительная проверка и разрешённое состояние повторов. У перечисленных ниже команд `--package` имеет значение по умолчанию и не является обязательным аргументом парсера; остальные требования указаны в таблице.

| Команда | Обязательные аргументы | Что меняет или запускает |
|---|---|---|
| `preflight-phase1-session` | `--output-root`, `--secret-root`, `--expected-secret-fingerprint`; необязательный `--package` | Запускает контейнеры и подготовку захвата, создаёт временные каталоги; не является проверкой только для чтения |
| `run-one-phase1-session` | Те же аргументы плюс `--confirm-execution-token`, `--confirm-one-unit` | Запускает одну научную единицу, создаёт PCAP, журналы Zeek, запись сопоставления и записи журнала |
| `recover-phase1-sealed-completion` | `--output-root`, `--secret-root`, `--expected-secret-fingerprint`, `--confirm-attempt-id`; необязательный `--package` | Восстанавливает только разрешённое запечатанное завершение и меняет состояние журнала |
| `run-technical-smoke` | `--confirm-disposable`, `--output-dir` | Создаёт временные сетевые данные |
| `run-factor-orthogonality-smoke` | `--confirm-disposable`, `--output-dir`, необязательный `--diagnostic-first-only` | Создаёт временные диагностические данные |

`run-one-phase1-session` нельзя копировать в обычную проверку и нельзя направлять его результат в отслеживаемую область репозитория. Восстановление не запускает поведение второй раз. Ни одна из этих команд не была запущена в рамках исправления документации.

## Лабораторная консоль

```powershell
$env:FILIN_CONSOLE_TOKEN = "локальный-одноразовый-токен"
python -m lab_console --host 127.0.0.1 --port 8043
```

Консоль слушает только localhost и записывает изменяемый слой в `runtime/lab_console/`. Проверки цикла:

```powershell
python -m tools.lab_console.verify_console
python -m tools.lab_console.verify_v044
python -m tools.lab_console.verify_v045
python -m tools.lab_console.verify_v046
python -m tools.lab_console.verify_v047
```

## Как читать результат

Успешная команда подтверждает только свой контракт. Она не означает внешнюю валидность, истинность гипотезы, научный pass, готовность к промышленной эксплуатации, право регистрации кандидата или разрешение автоматического ответа. Фактические числа регрессии фиксируются в отчёте конкретного окружения; baseline описан в [тестировании](../getting-started/testing.md).

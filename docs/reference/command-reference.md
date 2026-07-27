---
doc_schema: filin_document_v2
title: Справочник команд
document_type: reference
audience:
  - developer
  - auditor
  - operator
lifecycle: current
authoritative_for:
  - safe_command_registry
source_of_truth:
  - tools
  - pyproject.toml
last_reviewed_stage: v0.4.4
generated: false
evidence_immutable: false
---

# Справочник команд

Все команды выполняются из корня репозитория, если не указано иное.

## Подготовка среды

| Команда | Назначение | Меняет файлы | Runtime | Сеть | Ожидаемый итог | Ограничение |
|---|---|---:|---:|---:|---|---|
| `python -m pip install -r requirements.txt` | установить dependencies | environment | нет | возможно | packages доступны | не менять lock без этапа |

## Полный pytest и compileall

| Команда | Назначение | Меняет файлы | Runtime | Сеть | Ожидаемый итог | Ограничение |
|---|---|---:|---:|---:|---|---|
| `python -m pytest -q` | полный regression | нет | да | нет | `0 failed` | может быть длительным |
| `python -m compileall backend collectors incident_reconstruction lab_console ml rehearsal staging tools` | syntax/import bytecode check | `__pycache__` | да | нет | exit 0 | не является functional test |

## Документация

| Команда | Назначение | Меняет файлы | Runtime | Сеть | Ожидаемый итог | Ограничение |
|---|---|---:|---:|---:|---|---|
| `python -m tools.docs.build_documentation_inventory` | перестроить inventory/protected registry | docs/audit | нет | нет | deterministic files | запускать после content changes |
| `python -m tools.docs.validate_documentation_v2 --strict` | все правила Documentation v2 | нет | нет | нет | valid | findings не скрывать |
| `python -m tools.docs.run_documentation_campaign` | positive/negative campaign | audit + runtime | да | нет | все scenarios passed/rejected | temporary fixtures only |

## Status и authority

| Команда | Назначение | Меняет файлы | Runtime | Сеть | Ожидаемый итог | Ограничение |
|---|---|---:|---:|---:|---|---|
| `python -m tools.docs.validate_project_status --strict` | status consistency | нет | нет | нет | exit 0 | YAML имеет приоритет |
| `python -m tools.docs.validate_documentation_authority` | authoritative sources | нет | нет | нет | exit 0 | не создаёт status |
| `python -m tools.docs.validate_documentation_immutability` | frozen bytes | нет | нет | нет | exit 0 | baseline mismatches — warning |

## Candidate integrity и bundles

| Команда | Назначение | Меняет файлы | Runtime | Сеть | Ожидаемый итог | Ограничение |
|---|---|---:|---:|---:|---|---|
| `python -m tools.audit.validate_v03154_bundle` | candidate bundle | нет | нет | нет | valid | не rebuild frozen artifact |
| `python -m tools.audit.validate_v0318_bundle` | external-review bundle | нет | нет | нет | valid | не запускает external trial |
| `python -m tools.audit.validate_v042_bundle` | v0.4.2 reconstruction bundle | нет | нет | нет | valid | laboratory scope |

## Console и operator cycle

| Команда | Назначение | Меняет файлы | Runtime | Сеть | Ожидаемый итог | Ограничение |
|---|---|---:|---:|---:|---|---|
| `python -m lab_console --host 127.0.0.1 --port 8043` | localhost console | нет | да | localhost | UI доступен | token обязателен, public bind запрещён |
| `python -m tools.lab_console.verify_console` | standalone console verifier | нет | да | нет | passed | не production probe |
| `python -m tools.lab_console.verify_v044` | case catalog/operator workflow | нет | да | нет | policy valid | не запускает новый cycle |

## Безопасное воспроизведение

Используйте reproduction guide конкретного stage из [reports index](../reports/index.md).
Команда должна ссылаться на существующий versioned tool, писать только в разрешённый
runtime и не использовать production capture, secrets или external connections.

---
doc_schema: filin_document_v2
title: Архитектура лабораторной консоли
document_type: architecture
audience:
  - developer
  - operator
lifecycle: current
authoritative_for:
  - lab_console_architecture
source_of_truth:
  - lab_console
  - lab_console/contracts
last_reviewed_stage: v0.4.4
generated: false
evidence_immutable: false
---

# Архитектура лабораторной консоли

## Контуры

- FastAPI обслуживает только `127.0.0.1`;
- token authentication защищает локальную сессию;
- adapters читают frozen reports и case bundles;
- Jinja templates и статические ресурсы строят operator views;
- SQLite хранит только review sessions, progress, notes и decisions;
- export сериализует overlay и source identity детерминированно.

## Разделение хранения

Source bundle, manifest и semantic SHA остаются read-only. Изменяемые данные
записываются в `runtime/lab_console/` и не считаются evidence. Удаление runtime
overlay не меняет исходную карточку.

## Allowlist

Консоль допускает только заранее определённые локальные задачи и известные routes.
Она не запускает shell-команды пользователя, production capture или network actions.

Практический запуск описан в [руководстве](../getting-started/laboratory-console.md),
а файлы компонента — в [README](../../lab_console/README.md).

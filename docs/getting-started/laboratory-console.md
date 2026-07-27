---
doc_schema: filin_document_v2
title: Запуск лабораторной консоли
document_type: guide
audience:
  - operator
  - developer
lifecycle: current
authoritative_for:
  - console_launch_guide
source_of_truth:
  - lab_console/__main__.py
  - lab_console/app.py
last_reviewed_stage: v0.4.4
generated: false
evidence_immutable: false
---

# Запуск лабораторной консоли

## Безопасная область

Консоль предназначена только для localhost и синтетического каталога v0.4.4.
Она не является SIEM, production backend или средством автоматического реагирования.

## Запуск

```powershell
$env:FILIN_CONSOLE_TOKEN = "локальный-одноразовый-токен"
python -m lab_console --host 127.0.0.1 --port 8043
```

Откройте `http://127.0.0.1:8043/ui/cases`, вставьте token и завершите login.
Не публикуйте token и не изменяйте host на внешний интерфейс.

## Что записывается

SQLite overlay в `runtime/lab_console/` содержит session progress, item states,
notes и decision. Source bundles читаются без изменения. Token не сохраняется в Git.

## Страницы

Каталог ведёт к overview, facts, timeline, graph, gaps, hypotheses, comparisons,
questions, review и export. Справка доступна в интерфейсе и в
[руководстве по карточкам](reviewing-laboratory-cards.md).

## Проверка

```powershell
python -m tools.lab_console.verify_v044
```

Архитектура и API описаны в [README компонента](../../lab_console/README.md).

---
doc_schema: filin_document_v2
title: Устранение неполадок
document_type: guide
audience:
  - developer
  - operator
lifecycle: current
authoritative_for: []
source_of_truth:
  - lab_console
  - tools/docs
last_reviewed_stage: v0.4.4
generated: false
evidence_immutable: false
---

# Устранение неполадок

## Консоль не открывается

Проверьте, что порт 8043 свободен, process запущен из корня репозитория и host равен
`127.0.0.1`. Не заменяйте его на публичный bind.

## Вход отклонён

Создайте новый локальный `FILIN_CONSOLE_TOKEN` и повторите login. Не записывайте token
в tracked-файл или журнал issue.

## Интерфейс показывает старую версию

Перезапустите процесс console и выполните hard reload браузера. Static resources
имеют cache-busting version; ручное редактирование frozen reports не требуется.

## Тесты оставили runtime

Проверьте `git status`. Удаляйте только воспроизводимые untracked файлы внутри
`runtime/`, убедившись, что путь относится к текущему репозиторию. Не удаляйте tracked evidence.

## Documentation validator сообщает ошибку

Исправьте первопричину, затем перестройте inventory:

```powershell
python -m tools.docs.build_documentation_inventory
python -m tools.docs.validate_documentation_v2 --strict
```

Не отключайте правило и не перегенерируйте frozen artifact для маскировки finding.

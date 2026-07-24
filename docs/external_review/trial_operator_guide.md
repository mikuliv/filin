# Руководство trial operator

Operator получает только blind inputs, frozen candidate runtime и отдельный
prediction namespace. До prediction freeze ему запрещён доступ к labels.
Inference запускается без сети и backend. После validation оператор создаёт
prediction commitment и прекращает любые изменения submission. Повторный запуск
после label reveal требует новой protocol revision и не заменяет первый итог.

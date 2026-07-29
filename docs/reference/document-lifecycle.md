# Жизненный цикл документов

| lifecycle | Значение | Разрешённое изменение |
|---|---|---|
| `current` | текущий канонический документ | обычный reviewed Коммит |
| `historical` | описание завершённого состояния | только явная errata/навигация |
| `redirect` | совместимый старый путь | только смена canonical target |
| `generated` | представление реестра/дерева | только через generator |
| Зафиксировано | bytes входят в protected set | изменение запрещено |

Metadata всех tracked Markdown хранится в каноническом
[`documentation_inventory_v2.json`](../audit/documentation_inventory_v2.json).
Человекочитаемые страницы начинаются с H1 и не показывают служебный YAML Служебный заголовок.
Зафиксировано files не получают metadata внутри собственных неизменяемых bytes.

Перед перемещением проверяются incoming links и manifests. Старый путь сохраняется
перенаправление, если он публичен, исторически упомянут или contractually referenced.

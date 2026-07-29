# Сопровождение документации

## Порядок

1. Проверить branch, HEAD и clean tree.
2. Построить protected set из manifests/ledgers/protocols/detached SHA.
3. Снять inventory и SHA baseline.
4. Классифицировать текущий, исторический, перенаправление, generated и Зафиксировано documents.
5. Изменять только mutable files.
6. Обновить links, indexes и status views.
7. Перестроить inventory.
8. Выполнить validators, Кампании и full pytest.
9. Проверить protected bytes и clean diff.

## Зафиксировано conflict

Если устаревший документ защищён манифест, создайте новую редакцию или errata.
Не добавляйте Служебный заголовок и не исправляйте опечатку внутри Зафиксировано bytes.

## Перемещение

Сохраняйте перенаправление при incoming links, историческом упоминании, contractual path
или внешнем использовании. Обновляйте migration report.

## Завершение

Maintenance Коммит не меняет research status, candidate identity или allowed stages.

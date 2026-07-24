# Начало работы с проектом

«Филин» — исследовательская платформа анализа сетевых наблюдений. Основной
пользовательский маршрут начинается с [корневого README](../../README.md), затем
переходит к [текущему статусу](../status/current-status.md) и
[архитектуре](../architecture/overview.md).

Проект не имеет единого универсального production entrypoint. Отдельные
исследовательские и runtime-компоненты запускаются только в рамках
соответствующих versioned protocols. Реальный capture, внешняя сеть, backend и
automatic actions не входят в быстрый старт.

Перед изменением кода:

1. Прочитайте machine-readable [project status](../status/project-status.yaml).
2. Определите, относится ли изменение к current implementation или history.
3. Выполните подходящие unit tests.
4. Запустите документационные и artifact validators.

Для общей проверки используйте [руководство по тестированию](testing.md).

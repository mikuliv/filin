# Приёмка интерфейса v0.4.3.1

Статус: **пройдено**.

Интерфейс проверен в реально запущенной авторизованной локальной консоли. Все 16 обязательных экранов визуально просмотрены; уникальные view models, отсутствие горизонтального переполнения страницы и закрытое состояние raw JSON подтверждены браузерным проходом.

## Покрытие

- dashboard: 8 информационных карточек;
- этапы: 11 карточек двух линий;
- модели: 1 frozen-кандидат;
- показатели: 6 основных показателей и 5 строк классов;
- комплекты: 4;
- карточки инцидентов: 1;
- timeline: 7 элементов;
- graph: 29 узлов и 76 рёбер;
- гипотезы: 6 нейтральных карточек;
- матрица: 6×6;
- задачи: 6;
- тестовые результаты: 7;
- сценарии: 58 положительных и 65 отрицательных;
- скриншоты: 16.

Целевая регрессия: 92 passed. Полный `pytest`: 1683 passed, 0 failed, 3 warnings.

## Скриншоты

1. `runtime/lab_console/v0_4_3_1/screenshots/01-dashboard-1920x1080.jpg`
2. `runtime/lab_console/v0_4_3_1/screenshots/02-dashboard-1366x768.jpg`
3. `runtime/lab_console/v0_4_3_1/screenshots/03-stages.jpg`
4. `runtime/lab_console/v0_4_3_1/screenshots/04-model.jpg`
5. `runtime/lab_console/v0_4_3_1/screenshots/05-metrics.jpg`
6. `runtime/lab_console/v0_4_3_1/screenshots/06-bundles.jpg`
7. `runtime/lab_console/v0_4_3_1/screenshots/07-incidents.jpg`
8. `runtime/lab_console/v0_4_3_1/screenshots/08-incident-overview.jpg`
9. `runtime/lab_console/v0_4_3_1/screenshots/09-timeline.jpg`
10. `runtime/lab_console/v0_4_3_1/screenshots/10-graph.jpg`
11. `runtime/lab_console/v0_4_3_1/screenshots/11-hypotheses.jpg`
12. `runtime/lab_console/v0_4_3_1/screenshots/12-comparison-matrix.jpg`
13. `runtime/lab_console/v0_4_3_1/screenshots/13-questions.jpg`
14. `runtime/lab_console/v0_4_3_1/screenshots/14-tasks.jpg`
15. `runtime/lab_console/v0_4_3_1/screenshots/15-tests.jpg`
16. `runtime/lab_console/v0_4_3_1/screenshots/16-system.jpg`

SHA-256 и фактические размеры каждого снимка зафиксированы в `browser_acceptance.json`.

## Проверенные взаимодействия

Фильтр линий этапов, переключение слоя timeline, выбор узла графа, открытие объяснения ячейки матрицы, раскрытие raw-панели и сворачивание sidebar работают. Авторизация, CSRF, экранирование, security headers и allowlist задач сохранены.

## Известные ограничения

Скриншоты являются локальными runtime-артефактами и не коммитятся. Внутренний горизонтальный скролл допустим только для матрицы и широких таблиц. Интерфейс не является production, не доказывает причинность/компрометацию и не выбирает окончательную гипотезу.

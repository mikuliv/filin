# Коррекция отображения metadata Обслуживание документации v2.1

## Обнаруженная проблема

GitHub отображал YAML Служебный заголовок как служебную таблицу перед H1. В результате
корневой README и другие пользовательские страницы начинались не с содержания,
а с полей `doc_schema`, `audience`, `lifecycle` и `source_of_truth`.

## Объём коррекции

- исходный HEAD: `4fec1ac2bf9cb8cc76a320fee636b32fbcae5b63`;
- найдено tracked Markdown с видимым Служебный заголовок: **91**;
- исправлено: **91**;
- затронуто Зафиксировано подтверждающие материалы: **0**;
- новый канонический источник metadata:
  [`documentation_inventory_v2.json`](documentation_inventory_v2.json).

Inventory хранит schema, тип документа, аудиторию, lifecycle, authority domains,
авторитетный источник, reviewed stage, generated/подтверждающие материалы flags, актуальные SHA и действие.
Metadata не дублируется в отдельном авторитетном реестре.

## Изменения валидаторов

Валидаторы читают metadata из inventory и больше не требуют YAML Служебный заголовок.
Проверяются полнота покрытия, соответствие пути и H1, допустимый lifecycle,
уникальность authority, существование файловых авторитетный источник, соответствие
protected set, SHA и `actual_action`. Видимый YAML и служебная таблица метаданных
теперь являются ошибками.

Кампания включает **109** положительных и **92** отрицательных случая. В неё входят
два варианта каждого обязательного нарушения v2.1: YAML в README/guide, отсутствие
и расхождение metadata, дубли authority, отсутствующий source, неверный lifecycle,
mutable Зафиксировано подтверждающие материалы и видимая таблица метаданных.

## Визуальная приёмка

Эквивалентный локальный CommonMark renderer (`markdown-it-py`) проверил:

- `README.md`;
- `docs/index.md`;
- `docs/status/current-status.md`;
- `docs/architecture/overview.md`;
- `docs/getting-started/laboratory-console.md`;
- `docs/getting-started/reviewing-laboratory-cards.md`;
- `backend/README.md`;
- `incident_reconstruction/README.md`;
- `lab_console/README.md`.

Для всех страниц H1 является первым отображаемым элементом, metadata не видна,
H1 не дублируется, Mermaid распознаётся, таблицы не превышают установленную ширину,
локальные ссылки и anchors разрешаются. комментарий HTML в контрольном примере
не попадает в видимый текст.

## Неизменяемые границы

Candidate, серверная часть tree, protected подтверждающие материалы, manifests, policy results и научные
результаты не изменяются. `v0.3.19` и `v0.4.5` остаются только следующими
разрешёнными этапами; эта коррекция не является ни одним из них.

## Проверки

Итоговые результаты находятся в
[`documentation_validation_result_v2.json`](documentation_validation_result_v2.json):

- strict documentation, authority, freshness, immutability и terminology validators: пройдено;
- rendering acceptance: 9/9;
- documentation tests: 15 пройдено;
- console Средство проверки и v0.4.4 Средство проверки: пройдено;
- Проверка компиляции: пройдено;
- полный pytest: **1756 пройдено**, **0 ошибка**, **3 предупреждения**.

Три предупреждения sklearn относятся к вырожденным классам в исторических
`test_v036_group_metrics` и `test_v037_group_metrics`. 49 baseline манифест SHA
предупреждения существовали до v2.1, перечисляются validator и не скрываются.

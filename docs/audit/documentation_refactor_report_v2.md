# Итоговый отчёт Обслуживание документации v2

> Rendering correction v2.1: видимый YAML Служебный заголовок удалён из 91
> пользовательского документа из-за отображения GitHub. Канонические metadata
> сохранены в [inventory Файлы JSON](documentation_inventory_v2.json); подробности — в
> [отчёте v2.1](documentation_rendering_correction_v2_1.md).

## Опорные значения

- ветка: `main`;
- Зафиксировано HEAD v0.4.4: `80680bf8e890742e1c82929d7a2e8cd099a1b1ad`;
- исходный maintenance HEAD: `e97224a3f01a40cad83f88a35df922344088dd24`;
- candidate: `v03154:65a3dd912d845bc1`;
- серверная часть tree: `04218a4eb01534950efd5f7d6390f1a575cacbc8`;
- итоговый Коммит: Коммит, содержащий этот отчёт (точный SHA сообщается после создания Коммит);
- push: не выполнялся этим проходом.

## Объём

Исходно перед v2 в репозитории было **218** tracked документов Markdown; сам v2
довёл набор до 261 документа. После rendering correction v2.1 актуальный
[inventory Файлы JSON](documentation_inventory_v2.json) учитывает **262** документа:
**1** создан в v2.1, **76** переписаны удалением Служебный заголовок, **15** являются
redirects. Из них **177** текущий, **85** исторический, **6** generated и **61**
файл Markdown входит в protected set. После проверки осталось **0** broken links
и **0** broken anchors.

## Устранённые противоречия

- текущий architecture теперь описывает завершённый v0.4.4, а не planned v0.4.x;
- статус разделён на mainline v0.3.18→v0.3.19 и laboratory v0.4.4→v0.4.5;
- исторический серверная часть, old incident endpoints, MITRE/Sigma и modeling отделены;
- repository layout и testing включают reconstruction, console и operator Средство проверки;
- contracts/protocols/reports indexes строятся из repository tree;
- glossary, terminology, limitations и documentation style централизованы;
- `lab_console` получил полный README; protected incident README получил внешнюю текущий edition;
- old public paths сохранены redirects.

## Проверки

машиночитаемый результаты находятся в [проверка Файлы JSON](documentation_validation_result_v2.json).
Он включает structural validators, links/anchors, status, authority, terminology,
immutability, positive/negative Кампании и технические прогоны.

- Обслуживание документации v2: **103/103** positive и **86/86** negative;
- полный `pytest` после v2.1: **1756 пройдено**, **0 ошибка**, 3 предупреждения sklearn;
- documentation tests: **15 пройдено**;
- console regression: **161 пройдено**;
- v0.4.4 Средство проверки: **84** positive и **120** negative cases;
- terminology validator: 0 оставшихся нарушений;
- `compileall`, console Средство проверки, v0.3.15.4 артефакт проверка и v0.3.18 комплект: пройдено.

## Protected подтверждающие материалы

Protected set построен из manifests, ledgers, protocols и detached SHA. Files,
изменённые до этого maintenance относительно старых манифест entries, отражены как
baseline предупреждения; текущий проход не меняет их baseline bytes. Зафиксировано candidate,
серверная часть tree и v0.4.4 подтверждающие материалы проверяются повторно после edits.

## Ограничения

- документация не подтверждает external applicability;
- exact Коммит SHA не может быть записан внутрь того же Коммит без self-reference;
- remote URL и network links не проверяются содержательно;
- Зафиксировано documents сохраняют исторический язык и metadata вне собственных bytes.
- строгие исторические комплект validators v0.3.15.4 и v0.4.0–v0.4.2 сообщают о
  shared состояние текущий/файлах README, закономерно изменённых последующими этапами;
  актуальные проверки v0.3.15.4 artifacts, v0.3.18 и v0.4.4 при этом проходят.

## Сохранённые границы

`v0.3.19` остаётся package рассмотрение/trial-plan agreement; `v0.4.5` остаётся не
реализованным следующим laboratory stage. Candidate, модель, contracts, серверная часть и
Зафиксировано scientific results этим проходом не изменяются.

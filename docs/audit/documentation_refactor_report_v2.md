# Итоговый отчёт Documentation Maintenance v2

> Rendering correction v2.1: видимый YAML front matter удалён из 91
> пользовательского документа из-за отображения GitHub. Канонические metadata
> сохранены в [inventory JSON](documentation_inventory_v2.json); подробности — в
> [отчёте v2.1](documentation_rendering_correction_v2_1.md).

## Опорные значения

- ветка: `main`;
- frozen HEAD v0.4.4: `80680bf8e890742e1c82929d7a2e8cd099a1b1ad`;
- исходный maintenance HEAD: `e97224a3f01a40cad83f88a35df922344088dd24`;
- candidate: `v03154:65a3dd912d845bc1`;
- backend tree: `04218a4eb01534950efd5f7d6390f1a575cacbc8`;
- итоговый commit: commit, содержащий этот отчёт (точный SHA сообщается после создания commit);
- push: не выполнялся этим проходом.

## Объём

Исходно перед v2 в репозитории было **218** tracked Markdown-документов; сам v2
довёл набор до 261 документа. После rendering correction v2.1 актуальный
[inventory JSON](documentation_inventory_v2.json) учитывает **262** документа:
**1** создан в v2.1, **76** переписаны удалением front matter, **15** являются
redirects. Из них **177** current, **85** historical, **6** generated и **61**
Markdown-файл входит в protected set. После проверки осталось **0** broken links
и **0** broken anchors.

## Устранённые противоречия

- current architecture теперь описывает завершённый v0.4.4, а не planned v0.4.x;
- статус разделён на mainline v0.3.18→v0.3.19 и laboratory v0.4.4→v0.4.5;
- historical backend, old incident endpoints, MITRE/Sigma и modeling отделены;
- repository layout и testing включают reconstruction, console и operator verifier;
- contracts/protocols/reports indexes строятся из repository tree;
- glossary, terminology, limitations и documentation style централизованы;
- lab_console получил полный README; protected incident README получил внешнюю current edition;
- old public paths сохранены redirects.

## Проверки

Machine-readable результаты находятся в [validation JSON](documentation_validation_result_v2.json).
Он включает structural validators, links/anchors, status, authority, terminology,
immutability, positive/negative campaigns и технические прогоны.

- Documentation Maintenance v2: **103/103** positive и **86/86** negative;
- полный `pytest` после v2.1: **1756 passed**, **0 failed**, 3 предупреждения sklearn;
- documentation tests: **15 passed**;
- console regression: **161 passed**;
- v0.4.4 verifier: **84** positive и **120** negative cases;
- terminology validator: 0 оставшихся нарушений;
- `compileall`, console verifier, v0.3.15.4 artifact validation и v0.3.18 bundle: passed.

## Protected evidence

Protected set построен из manifests, ledgers, protocols и detached SHA. Files,
изменённые до этого maintenance относительно старых manifest entries, отражены как
baseline warnings; текущий проход не меняет их baseline bytes. Frozen candidate,
backend tree и v0.4.4 evidence проверяются повторно после edits.

## Ограничения

- документация не подтверждает external applicability;
- exact commit SHA не может быть записан внутрь того же commit без self-reference;
- remote URL и network links не проверяются содержательно;
- frozen documents сохраняют исторический язык и metadata вне собственных bytes.
- строгие исторические bundle validators v0.3.15.4 и v0.4.0–v0.4.2 сообщают о
  shared current-status/README-файлах, закономерно изменённых последующими этапами;
  актуальные проверки v0.3.15.4 artifacts, v0.3.18 и v0.4.4 при этом проходят.

## Сохранённые границы

`v0.3.19` остаётся package review/trial-plan agreement; `v0.4.5` остаётся не
реализованным следующим laboratory stage. Candidate, model, contracts, backend и
frozen scientific results этим проходом не изменяются.

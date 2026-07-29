# Каталог лабораторных случаев

`v0.4.4` содержит 12 независимых синтетических cases с уникальными card ID и
семантическая контрольная сумма. Они покрывают обычную активность, auth, beacon, clock uncertainty,
duplicates, equal support, incomplete подтверждающие материалы, late delivery, low load, mixed,
port scan и web probe.

## Назначение

Каталог проверяет навигацию, reconstruction views, competing гипотезы и persistent
operator порядок работы на предусмотренных структурах. Scenario labels и тестовый эталон не
попадают в среда выполнения payload.

## Ограничение

Двенадцать cases не являются representative sample реальных инцидентов. Они не
измеряют external модель quality и не разрешают deployment.

Зафиксировано identity находится в [комплект манифест](../../ml/reports/v0_4_4/v0_4_4_bundle_manifest.json),
а порядок работы — в [operator guide](../getting-started/reviewing-laboratory-cards.md).

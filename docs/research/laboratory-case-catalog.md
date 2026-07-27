---
doc_schema: filin_document_v2
title: Каталог лабораторных случаев
document_type: reference
audience:
  - researcher
  - operator
  - auditor
lifecycle: current
authoritative_for:
  - laboratory_case_catalog_summary
source_of_truth:
  - ml/reports/v0_4_4/v0_4_4_bundle_manifest.json
  - lab_console/cases
last_reviewed_stage: v0.4.4
generated: false
evidence_immutable: false
---

# Каталог лабораторных случаев

`v0.4.4` содержит 12 независимых синтетических cases с уникальными card ID и
semantic SHA. Они покрывают обычную активность, auth, beacon, clock uncertainty,
duplicates, equal support, incomplete evidence, late delivery, low load, mixed,
port scan и web probe.

## Назначение

Каталог проверяет навигацию, reconstruction views, competing hypotheses и persistent
operator workflow на предусмотренных структурах. Scenario labels и test oracle не
попадают в runtime payload.

## Ограничение

Двенадцать cases не являются representative sample реальных инцидентов. Они не
измеряют external model quality и не разрешают deployment.

Frozen identity находится в [bundle manifest](../../ml/reports/v0_4_4/v0_4_4_bundle_manifest.json),
а порядок работы — в [operator guide](../getting-started/reviewing-laboratory-cards.md).

---
doc_schema: filin_document_v2
title: Причинные признаки
document_type: reference
audience:
  - researcher
  - developer
lifecycle: current
authoritative_for: []
source_of_truth:
  - ml/features
  - ml/artifacts/v0_3_15_4/candidate_manifest.json
last_reviewed_stage: v0.4.4
generated: false
evidence_immutable: false
---

# Причинные признаки

`network_features_v2` содержит 51 признак, доступный в момент решения и допустимый
с точки зрения causal ordering. Контракт исключает post-outcome leakage и фиксирует
типы, порядок, preprocessing и missing-value policy.

## Назначение

Признаки обеспечивают воспроизводимый вход frozen candidate. Они не являются
описанием злоумышленника и не доказывают причинность отдельного инцидента.

## Целостность

Feature contract, preprocessing SHA и candidate manifest проверяются совместно.
Несовпадение identity должно приводить к отказу, а не silent migration.

## Ограничение

Лабораторная устойчивость представления не доказывает внешнюю переносимость.
Текущий candidate и lineage описаны в [отдельном справочнике](candidate-lineage.md).

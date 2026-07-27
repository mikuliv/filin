---
doc_schema: filin_document_v2
title: Каталог компонентов
document_type: reference
audience:
  - developer
  - auditor
lifecycle: current
authoritative_for:
  - component_directory
source_of_truth:
  - repository_tree
last_reviewed_stage: v0.4.4
generated: false
evidence_immutable: false
---

# Каталог компонентов

| Компонент | README | Контракты | Тестирование |
|---|---|---|---|
| Backend prototype | [backend](../../backend/README.md) | historical backend schemas | historical tests |
| Collectors | [collectors](../../collectors/README.md) | `collectors/**/contracts` | collector pytest |
| Datasets | [datasets](../../datasets/README.md) | provenance metadata | documentation/data tests |
| Lab | [lab](../../lab/README.md) | scenario/environment specs | lab pytest |
| ML | [ml](../../ml/README.md) | features, protocols, artifacts | full ML pytest |
| Staging | [staging](../../staging/README.md) | `staging/contracts` | staging tests |
| Rehearsal | [rehearsal](../../rehearsal/README.md) | `rehearsal/contracts` | rehearsal tests |
| Reconstruction | [incident_reconstruction](../../incident_reconstruction/README.md) | `incident_reconstruction/contracts` | v0.4.0–v0.4.2 tests |
| Console | [lab_console](../../lab_console/README.md) | `lab_console/contracts` | v0.4.3–v0.4.4 tests |
| External review | [external_review](../../external_review/README.md) | `external_review/contracts` | v0.3.18 validators |
| Tools | [tools](../../tools/README.md) | tool-specific CLI | documentation/bundle validators |

Архитектурные связи приведены в [component map](../architecture/component-map.md).

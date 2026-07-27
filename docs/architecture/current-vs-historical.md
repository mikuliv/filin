---
doc_schema: filin_document_v2
title: Текущие и исторические компоненты
document_type: architecture
audience:
  - newcomer
  - developer
  - auditor
lifecycle: current
authoritative_for:
  - current_historical_boundary
source_of_truth:
  - docs/status/project-status.yaml
  - docs/status/v0_4_track.yaml
last_reviewed_stage: v0.4.4
generated: false
evidence_immutable: false
---

# Текущие и исторические компоненты

## Текущие

- candidate lineage и `network_features_v2`;
- `shadow_event_v2`;
- staging/reference receiver как изолированный лабораторный transport;
- `incident_reconstruction/` в состоянии `v0.4.0–v0.4.4`;
- `lab_console/` и operator workflow v0.4.4;
- frozen external-review package как подготовленный объект проверки.

## Исторические или демонстрационные

- `backend/` и ранние incident endpoints;
- статический MITRE prototype;
- прежний Sigma generator;
- ранние model profiles и training plans;
- superseded event contracts;
- старые интеграционные обещания, отменённые последующими policy results.

## Старые пути документации

`docs/modeling.md`, `docs/incident-workflow.md`, `docs/mitre-mapping.md` и
`docs/sigma-generation.md` сохранены как короткие redirects к историческому слою.
Они не являются источниками текущей архитектуры.

См. [исторический backend](../history/historical-backend.md),
[историческое моделирование](../history/historical-modeling.md) и
[MITRE/Sigma](../history/historical-mitre-and-sigma.md).

---
doc_schema: filin_document_v2
title: Принципы оценки
document_type: reference
audience:
  - researcher
  - auditor
lifecycle: current
authoritative_for: []
source_of_truth:
  - frozen_protocols
last_reviewed_stage: v0.4.4
generated: false
evidence_immutable: false
---

# Принципы оценки

## До запуска

Фиксируются scope, candidate, data split, seed namespace, contracts, metrics,
absolute gates, relative comparisons, stop conditions и prohibited adaptation.

## Во время запуска

Run journal сохраняет команды, environment identity, timestamps и failures.
Непредусмотренный input отклоняется. Missing evidence не заменяется предположением.

## После запуска

Policy result выводится из frozen gates. Manifest и detached SHA связывают artifacts.
Claim ledger показывает, какой artifact поддерживает каждое утверждение.

## Отрицательный результат

Failure сохраняется и ограничивает следующий stage. Corrective stage не переписывает
историческую policy; он создаёт новый protocol и новые evidence.

## Лабораторная линия

Успех v0.4 означает корректность предусмотренной reconstruction/operator procedure,
а не новое подтверждение качества model на внешних данных.

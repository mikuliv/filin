# Подтверждённые возможности

Каждое утверждение ниже ограничено evidence scope указанного этапа.

## Causal feature extraction

- Scope: 51-признаковое causal representation.
- Supporting stage: v0.3.15.4 и последующие candidate evaluations.
- Limitation: лабораторные datasets и frozen contract.
- Evidence: [candidate lineage](../research/candidate-lineage.md).

## Frozen scientific evaluation

- Scope: independent holdout для current development candidate.
- Supporting stage: v0.3.15.5.
- Limitation: не real organization trial.
- Evidence: [описание v0.3.15.5](../experiments/v0_3_15_5.md).

## Passive runtime и staging delivery

- Scope: local passive events, at-least-once delivery и verified receiver.
- Supporting stages: v0.3.15.5.1 и v0.3.16.
- Limitation: reference receiver не является backend.
- Evidence: [delivery runtime](../architecture/delivery-runtime.md).

## Длительная local campaign

- Scope: четыре часа synthetic local workload.
- Supporting stage: v0.3.17.
- Limitation: stage policy завершилась отрицательно; результат сохранён.
- Evidence: [v0.3.17](../experiments/v0_3_17.md).

## Corrective timing validation

- Scope: anchors, timing instrumentation, corruption/finalization и targeted
  trial.
- Supporting stage: v0.3.17.1.
- Limitation: не external trial.
- Evidence: [v0.3.17.1](../experiments/v0_3_17_1.md).

## External review protocol

- Scope: contracts, commitments, evaluator, package verifier и synthetic
  rehearsal.
- Supporting stage: v0.3.18.
- Limitation: real data/model не использовались; scientific evidence=false.
- Evidence: [external review overview](../external_review/README.md).

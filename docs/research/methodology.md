# Исследовательская методология

Методология разделяет development, frozen evaluation и runtime validation.
Данные, использованные для fit, calibration, conformal logic или threshold
selection, не могут одновременно подтверждать независимый результат.

Основные правила:

- features используют только causal information;
- candidate и критерии замораживаются до evaluation;
- split выполняется по episodes, времени, nodes, environments и origins;
- scientific metrics и runtime gates оцениваются раздельно;
- отрицательные результаты и invalidated revisions сохраняются;
- claims ограничиваются scope конкретного evidence bundle.

Blind external evaluation дополнительно требует dataset, label, candidate,
evaluator и prediction commitments. v0.3.18 проверил этот protocol только на
synthetic fixtures.

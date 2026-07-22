# Дорожная карта

Статус v0.3.15.5: promotion отклонён из-за frozen event-contract mismatch. Следующий допустимый этап — v0.3.15.5.1: заранее замороженная candidate-compatible коррекция контракта и новая runtime campaign. Текущий holdout нельзя повторно использовать для подбора; v0.3.16 остаётся заблокирован.

Источник текущего решения: [`status/project-status.yaml`](status/project-status.yaml).

## Хронология

<!-- stage-history:start -->
- v0.3.1 — базовая оценка.
- v0.3.2 — проверка устойчивости зафиксированной модели.
- v0.3.3 — completed, negative result.
- v0.3.4 — completed training redesign.
- v0.3.5 — completed frozen regression.
- v0.3.6 — completed holdout, negative policy.
- v0.3.7 — completed training cycle, negative policy.
- v0.3.8 — completed uncertainty cycle, negative policy.
- v0.3.9 — completed episode-first cycle, negative policy.
- v0.3.10 — completed minimal probabilistic cycle, negative policy.
- v0.3.10.1 — completed corrective clarification.
- v0.3.11 — completed training; historical frozen candidate preserved.
- v0.3.12 — completed regression, negative policy.
- v0.3.12.1 — completed causal-order audit.
- v0.3.12.2 — completed corrected regression.
- v0.3.13 — completed independent environmental holdout.
- v0.3.14 — completed component/contract audit; scope subsequently reassessed.
- v0.3.15 — completed local passive trial; runtime claims subsequently reassessed.
- v0.3.15.1 — completed corrective runtime evidence hardening.
- v0.3.15.2 — completed negative prospective integrated runtime trial.
- v0.3.15.3 — completed scientific regression analysis; mixed cause established.
- v0.3.15.4 — completed controlled redevelopment; candidate ready only for v0.3.15.5 prospective evaluation.
- v0.3.15.5 — completed independent holdout; scientific gates passed, runtime contract failed, candidate not promoted.
<!-- stage-history:end -->

## Ближайшая работа

v0.3.16 имеет статус blocked. Следующая работа — новый независимый prospective holdout v0.3.15.5 для candidate v0.3.15.4 с полным ACK, latency, CPU и privacy evidence.

## v0.3.16

После положительного нового runtime trial допустимо только проектирование staging-only receiver и read-only operator workflow. Это не разрешает production connection, изменение backend или automatic actions.

## v0.4.x

Отдельная архитектурная ветка может исследовать governance, staging transport, access control, retention и внешний validation protocol. Она не смешивается с evidence reconstruction v0.3.15.1.

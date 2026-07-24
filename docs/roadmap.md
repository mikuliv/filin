# Дорожная карта

Статус v0.3.17.1: корректирующий аудит и 45-минутный targeted trial завершены с положительным policy result. Разрешён только design review v0.3.18; shadow mode и backend integration не разрешены.

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
- v0.3.15.5.1 — completed prospective runtime recovery; contract, registry, 12/12 faults и composite promotion passed.
- v0.3.16 — completed isolated staging transport; 2 280/2 280 events, 24/24 faults и 59/59 gates passed.
- v0.3.17 — completed controlled local rehearsal; 4 часа wall-clock и 201 420 reconciled events, но historical-anchor, clock/latency, performance и corruption/bundle gates failed.
- v0.3.17.1 — completed corrective audit; historical causes resolved, timing/performance evidence and 45-minute targeted trial passed.
<!-- stage-history:end -->

## Ближайшая работа

Разрешён только design review v0.3.18. Реальный trial, shadow mode, backend integration и production остаются запрещены.

## v0.3.16

После положительного нового runtime trial допустимо только проектирование staging-only receiver и read-only operator workflow. Это не разрешает production connection, изменение backend или automatic actions.

## v0.4.x

Отдельная архитектурная ветка может исследовать governance, staging transport, access control, retention и внешний validation protocol. Она не смешивается с evidence reconstruction v0.3.15.1.

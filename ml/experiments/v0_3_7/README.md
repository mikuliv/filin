# Филин v0.3.7 — новый цикл network sensor

Этап создан после отрицательного prospective holdout v0.3.6. Flat multiclass classifier смешивал сам факт suspicious activity с выбором attack subtype и систематически ошибался на новых benign workflows. v0.3.7 разделяет эти решения и явно представляет недостаток evidence.

## Изоляция данных

Training использует только 12 новых runs. Data guard блокирует пути v0.3.6, их известные SHA-256, symlink-обход и validation rows до freeze. v0.3.6 остаётся locked regression benchmark и не применяется для feature selection, model selection, calibration, OOD, abstention или temporal parameters.

## Архитектура

Порядок решения: causal feature builder → calibrated binary gate → benign OOD guard → abstention → calibrated subtype classifier → causal temporal accumulator. OOD не означает attack. `insufficient_evidence` не считается benign; `suspicious_unclassified` остаётся alert.

## Научный протокол

12 base combinations сравниваются nested grouped CV: outer 6, inner 4, grouping `run_id`. Calibration строится только из group-aware OOF probabilities. IsolationForest обучается только на benign training, а thresholds и temporal variant выбираются только по training OOF. После refit на 12 runs один candidate, feature schema, ordered features, calibrators, OOD threshold, abstention и temporal parameters фиксируются в `frozen_candidate_manifest.yaml`.

Internal validation состоит из шести новых runs и выполняется один раз. No-fit guard запрещает fit, partial_fit, calibration, threshold/OOD/temporal tuning и feature selection. Immutable predictions проверяются SHA-256; `--resume` не повторяет prediction phase.

## Ограничения

Успешная internal validation не доказывает generalization и не разрешает backend integration или shadow mode. Abstention не должен скрывать ошибки: отчёты всегда содержат closed-set и operational metrics. Runtime datasets, artifacts, predictions и reports находятся вне Git.

# Политика метрик

Frozen evaluator формирует confusion matrix, per-class precision/recall/F1,
macro и weighted F1, balanced accuracy, false-positive/false-negative counts,
abstention, coverage, selective accuracy, missing/duplicate/invalid counts,
episode metrics и uncertainty intervals.

Abstention не считается правильным ответом; missing prediction не заменяется
классом по умолчанию. Organization-specific thresholds и минимальный внешний
macro F1 остаются design requirements и должны быть согласованы до holdout
commitment. Post-hoc selection запрещён.

# Принципы оценки

До evaluation замораживаются candidate, evaluator, class taxonomy, aggregation,
metrics, abstention rules и stop conditions. Post-hoc threshold selection,
исключение неудобных samples и выбор averaging после раскрытия labels запрещены.

Scientific gates оценивают predictive behavior на допустимом holdout. Runtime
gates оценивают delivery, timing, durability, privacy и reproducibility.
Прохождение runtime gate не доказывает scientific accuracy, а scientific result
не разрешает production integration.

Negative outcome публикуется с тем же evidence discipline, что и positive
outcome.

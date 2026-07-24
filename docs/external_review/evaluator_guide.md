# Руководство independent evaluator

Evaluator проверяет полное соответствие episode IDs, duplicate/missing/invalid
predictions и abstention semantics. Он использует frozen class taxonomy,
aggregation и metrics, не меняет predictions/labels, не выбирает threshold и не
исключает samples post hoc. Повторный запуск на одинаковом входе обязан дать
байт-в-байт одинаковый canonical result.

# Frozen regression v0.3.12.2

Новый этап применяет неизменённый кандидат v0.3.11 к трём полным frozen bundles. v0.3.8 получает одну predict-only запись; v0.3.9 и v0.3.10 используют ссылки на immutable predictions v0.3.12. Stateful и episode metrics всегда начинаются с сортировки по `benchmark_id`, `run_id`, `activity_key`, `causal_order`, `immutable_row_id`.

Исторические v0.3.6 и v0.3.7 остаются `rebuildable_but_not_frozen` и заранее исключены из scientific denominator. Fit, calibration, tuning, feature extraction, Docker, Zeek, shadow mode и backend integration запрещены.

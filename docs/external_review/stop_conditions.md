# Условия остановки и invalidation

Trial останавливается или invalidates при раннем label reveal, изменении frozen
identity, overlap, commitment mismatch, missing provenance, unsupported input,
privacy/secret finding, external route, backend call, role/chronology conflict,
недостаточном sample plan, evaluator nondeterminism, неполном prediction set или
post-hoc exclusion.

Новая попытка после reveal не может заменить исходный результат и требует
отдельной revision.

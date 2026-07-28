# Итог v0.4.6

Создан один воспроизводимый laboratory-only proposal `proposal:v046:9d93cdc53689b0f5` из проверенных синтетических данных. Frozen split по `session_id` исключает пересечения ролей, leakage gate пройден, а два независимых выполнения frozen recipe дали byte-identical модель и одинаковые прогнозы.

После замораживания proposal выполнены internal screening, read-only сравнение с действующим кандидатом через контур v0.4.5, admission gate и сохраняемое ручное рассмотрение. Все обязательные критерии пройдены; решение — `admitted_to_separate_validation`.

Результат разрешает только подготовку отдельного протокола v0.4.7. Proposal не зарегистрировано как кандидат. Действующий candidate `v03154:65a3dd912d845bc1`, registry, backend и frozen материалы предыдущих этапов не изменены. Model binary и dataset не входят в Git или экспорт.

# Компонентная карта

| Компонент | Вход | Выход | Контракт | Проверка |
|---|---|---|---|---|
| `collectors/` | PCAP/Zeek observations | нормализованные записи и passive events | collector и event schemas | collector tests |
| `ml/features/` | нормализованные записи | `network_features_v2` | признак contract | признак tests |
| `ml/decision/` | Зафиксировано scores | episode decision | decision/state policy | ML campaign tests |
| `staging/` | контракт пассивного события (`shadow_event_v2`) | ACK и trace | staging contracts | staging tests |
| `rehearsal/` | локальный campaign plan | transport подтверждающие материалы | rehearsal contracts | rehearsal Средство проверки |
| `incident_reconstruction/` | passive event + подтверждающие материалы refs | facts, relations, разрывы, гипотезы, card | v0.4 schemas | v0.4 Средство проверки |
| `lab_console/` | laboratory card комплект | UI и manual рассмотрение экспорт | console/operator schemas | console Средство проверки |
| `external_review/` | Зафиксировано package | procedural results | рассмотрение внешнего contracts | package validators |
| `backend/` | исторические demo requests | demo responses | исторический schemas | исторический tests only |

Подробные README доступны через [каталог компонентов](../reference/component-directory.md).

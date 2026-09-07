# Компонентная карта

| Компонент | Вход | Выход | Контракт | Проверка |
|---|---|---|---|---|
| `collectors/` | PCAP/Zeek observations | нормализованные записи и passive events | collector и event schemas | collector tests |
| `ml/features/` | нормализованные записи | `network_features_v2` | контракт признаков | тесты признаков |
| `ml/decision/` | оценки зафиксированного кандидата | решение по эпизоду | политика решений и состояний | тесты ML-кампаний |
| `staging/` | контракт пассивного события (`shadow_event_v2`) | подтверждение приёма и trace | контракты staging | тесты staging |
| `rehearsal/` | локальный campaign plan | transport подтверждающие материалы | rehearsal contracts | rehearsal Средство проверки |
| `incident_reconstruction/` | passive event + подтверждающие материалы refs | facts, relations, разрывы, гипотезы, card | v0.4 schemas | v0.4 Средство проверки |
| `lab_console/` | laboratory card комплект | UI и manual рассмотрение экспорт | console/operator schemas | console Средство проверки |
| `external_review/` | зафиксированный пакет | результаты процедуры | рассмотрение внешних контрактов | проверки пакета |
| `backend/` | исторические demo requests | demo responses | исторический schemas | исторический tests only |

Подробные README доступны через [каталог компонентов](../reference/component-directory.md).

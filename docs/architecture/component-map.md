# Компонентная карта

| Компонент | Вход | Выход | Контракт | Проверка |
|---|---|---|---|---|
| `collectors/` | PCAP/Zeek observations | нормализованные записи и passive events | collector и event schemas | collector tests |
| `ml/features/` | нормализованные записи | `network_features_v2` | feature contract | feature tests |
| `ml/decision/` | frozen scores | episode decision | decision/state policy | ML campaign tests |
| `staging/` | `shadow_event_v2` | ACK и trace | staging contracts | staging tests |
| `rehearsal/` | локальный campaign plan | transport evidence | rehearsal contracts | rehearsal verifier |
| `incident_reconstruction/` | passive event + evidence refs | facts, relations, gaps, hypotheses, card | v0.4 schemas | v0.4 verifier |
| `lab_console/` | laboratory card bundle | UI и manual review export | console/operator schemas | console verifier |
| `external_review/` | frozen package | procedural results | external-review contracts | package validators |
| `backend/` | исторические demo requests | demo responses | historical schemas | historical tests only |

Подробные README доступны через [каталог компонентов](../reference/component-directory.md).

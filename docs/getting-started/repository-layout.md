# Структура репозитория

| Каталог | Назначение | Хранение | Статус | Основная проверка | Что запрещено |
|---|---|---|---|---|---|
| `backend/` | ранний API prototype | tracked | исторический | historical unit tests | считать текущим backend |
| `collectors/` | ingest, Zeek/Suricata/CSV, shadow runtime | tracked | текущий | collector tests | production capture без этапа |
| `datasets/` | правила и описания наборов | tracked metadata | текущий reference | provenance checks | коммитить чувствительные raw data |
| `docs/` | текущая документация, статус, история | tracked | текущий | documentation v2 validator | менять frozen evidence |
| `examples/` | безопасные примеры | tracked | справочный | example tests | реальные identifiers и secrets |
| `external_review/` | executable contracts внешней процедуры | tracked/frozen | ограниченный | package validator | запускать trial автоматически |
| `incident_reconstruction/` | facts, relations, gaps, hypotheses, cards | tracked | текущий лабораторный | v0.4 verifier | трактовать graph как causal proof |
| `lab/` | локальные стенды и сценарии | tracked | исследовательский | lab tests | выход из изоляции |
| `lab_console/` | localhost UI и operator overlay | tracked + runtime | текущий лабораторный | console verifier | публичный bind и automatic action |
| `ml/` | features, artifacts, protocols, reports | tracked/frozen | текущий и исторический | pytest и bundle validators | переписывать frozen reports |
| `rehearsal/` | локальная контролируемая репетиция | tracked + runtime | текущий лабораторный | rehearsal tests | считать внешним trial |
| `runtime/` | базы, логи, temp reports | runtime-only | изменяемый | cleanup/validators | считать evidence по умолчанию |
| `staging/` | reference receiver и transport | tracked + runtime | текущий лабораторный | staging tests | называть production backend |
| `tools/` | generators, validators, verifiers | tracked | текущий | tool-specific tests | обходить frozen policy |

README каждого компонента определяет входы, выходы и безопасные команды. Полный
каталог: [component-directory](../reference/component-directory.md).

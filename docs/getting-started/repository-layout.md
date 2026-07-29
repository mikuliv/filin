# Структура репозитория

| Каталог | Назначение | Хранение | Статус | Основная проверка | Что запрещено |
|---|---|---|---|---|---|
| `backend/` | ранний API prototype | tracked | исторический | исторический unit tests | считать текущим серверная часть |
| `collectors/` | ingest, Zeek/Suricata/CSV, shadow среда выполнения | tracked | текущий | collector tests | промышленная эксплуатация capture без этапа |
| `datasets/` | правила и описания наборов | tracked metadata | текущий reference | происхождение checks | коммитить чувствительные raw data |
| `docs/` | текущая документация, статус, история | tracked | текущий | documentation v2 validator | менять Зафиксировано подтверждающие материалы |
| `examples/` | безопасные примеры | tracked | справочный | example tests | реальные identifiers и secrets |
| `external_review/` | executable contracts внешней процедуры | tracked/Зафиксировано | ограниченный | package validator | запускать trial автоматически |
| `incident_reconstruction/` | facts, relations, разрывы, гипотезы, cards | tracked | текущий лабораторный | v0.4 Средство проверки | трактовать graph как causal proof |
| `lab/` | локальные стенды и сценарии | tracked | исследовательский | lab tests | выход из изоляции |
| `lab_console/` | localhost UI и operator изменяемый слой | tracked + среда выполнения | текущий лабораторный | console Средство проверки | публичный bind и automatic action |
| `ml/` | features, artifacts, protocols, reports | tracked/Зафиксировано | текущий и исторический | pytest и комплект validators | переписывать Зафиксировано reports |
| `rehearsal/` | локальная контролируемая репетиция | tracked + среда выполнения | текущий лабораторный | rehearsal tests | считать внешним trial |
| `runtime/` | базы, логи, temp reports | только в среде выполнения | изменяемый | cleanup/validators | считать подтверждающие материалы по умолчанию |
| `staging/` | reference receiver и transport | tracked + среда выполнения | текущий лабораторный | staging tests | называть промышленная серверная часть |
| `tools/` | generators, validators, verifiers | tracked | текущий | tool-specific tests | обходить Зафиксировано policy |

README каждого компонента определяет входы, выходы и безопасные команды. Полный
каталог: [component-directory](../reference/component-directory.md).

Лицензионные данные размещены в `LICENSES/`, `docs/licensing/`, `licensing/`, `distribution/profiles/` и `sbom/`. Генераторы и validators находятся в `tools/licensing/`; Зафиксировано-файлы получают назначение через `REUSE.toml` без изменения байтов.

---
doc_schema: filin_document_v2
title: Терминология документации
document_type: reference
audience:
  - contributor
lifecycle: current
authoritative_for:
  - terminology_policy
source_of_truth:
  - docs/reference/glossary.md
last_reviewed_stage: v0.4.4
generated: false
evidence_immutable: false
---

# Терминология документации

Русское понятное название используется первым, а technical identifier сохраняется
в скобках или code style. Имена JSON fields, enum values, paths, APIs и standards не переводятся.

| Предпочтительно | Не использовать как narrative |
|---|---|
| текущий | current |
| область | scope |
| утверждение | claim |
| подтверждающий материал | evidence |
| рассмотрение / экспертная проверка | review без пояснения |
| независимый эксперт | reviewer |
| испытание | trial |
| промышленная эксплуатация | production как обычное слово |
| порядок работы / рабочий цикл | workflow без пояснения |
| программа запуска | runner без пояснения |

Допустимы PCAP, Zeek, API, SQL, HTTP, SHA-256, MITRE ATT&CK и Sigma. Первое
употребление специального английского термина получает русское пояснение.

Нельзя заменять «гипотеза» словом «факт», «отношение» — «причиной», а
`better_supported` — словом «истина».

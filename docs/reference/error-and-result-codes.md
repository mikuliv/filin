---
doc_schema: filin_document_v2
title: Коды ошибок и результатов
document_type: reference
audience:
  - developer
  - operator
lifecycle: current
authoritative_for: []
source_of_truth:
  - versioned_contracts
  - tools/docs/validate_documentation_v2.py
last_reviewed_stage: v0.4.4
generated: false
evidence_immutable: false
---

# Коды ошибок и результатов

## Документация

Validator использует стабильные префиксы: `broken_link`, `broken_anchor`,
`h1_count`, `heading_jump`, `missing_front_matter`, `status_mismatch`,
`protected_file_changed`, `absolute_local_path`, `possible_secret`,
`orphan_current_document` и `redirect_cycle`.

## Матрица гипотез

- `equally_supported` — равная опора;
- `better_supported` — row hypothesis поддержана лучше column hypothesis;
- `less_supported` — row hypothesis поддержана слабее;
- `incomparable` — безопасное сравнение невозможно;
- `insufficient_data` — недостаточно сведений.

## Review

- `not_reviewed` — не рассмотрено;
- `reviewed` — рассмотрено без изменения evidence;
- `additional_evidence_required` — нужен новый материал;
- `unresolved` — остаётся открытым;
- `completed` — operator session завершена, не означает окончательного определения.

Точные enum и HTTP responses определяются соответствующей versioned schema/API.

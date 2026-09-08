# Коды ошибок и результатов

## Документация

Средство проверки использует стабильные префиксы: `broken_link`, `broken_anchor`,
`h1_count`, `heading_jump`, `missing_front_matter`, `status_mismatch`,
`protected_file_changed`, `absolute_local_path`, `possible_secret`,
`orphan_current_document` и `redirect_cycle`.

## Матрица гипотез

- `equally_supported` — равная опора;
- `better_supported` — гипотеза строки поддержана лучше гипотезы столбца;
- `less_supported` — гипотеза строки поддержана слабее гипотезы столбца;
- `incomparable` — безопасное сравнение невозможно;
- `insufficient_data` — недостаточно сведений.

## рассмотрение

- `not_reviewed` — не рассмотрено;
- `reviewed` — рассмотрено без изменения подтверждающие материалы;
- `additional_evidence_required` — нужен новый материал;
- `unresolved` — остаётся открытым;
- `completed` — сессия оператора завершена, но это не означает окончательного определения.

Точные перечисления и ответы HTTP определяются соответствующей версионированной схемой или API.

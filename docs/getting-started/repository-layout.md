# Структура репозитория

| Каталог | Назначение | Хранение | Статус и проверки |
|---|---|---|---|
| `backend/` | Отдельный исторический backend-код | tracked | Не интегрирован с current sensor/runtime path |
| `collectors/` | Collectors и passive event contracts | tracked | Unit и contract tests |
| `datasets/` | Описания и metadata наборов | tracked частично | Raw datasets в Git не добавляются |
| `docs/` | Текущая, историческая и review-документация | tracked | Documentation validators |
| `examples/` | Безопасные примеры | tracked | Не являются production configuration |
| `external_review/` | JSON Schemas внешней проверки | tracked | v0.3.18 contract tests |
| `lab/` | Локальные synthetic scenarios | tracked | Лабораторный scope |
| `ml/` | Features, candidates, experiments и reports | tracked частично | Model artifacts и raw runtime исключены |
| `rehearsal/` | Изолированные runtime contracts/configuration | tracked | Stage-specific validators |
| `runtime/` | Локальные generated artifacts | runtime-only | Не добавляется в Git |
| `staging/` | Изолированный staging transport | tracked | Не является backend |
| `tools/` | Validators, builders и audit utilities | tracked | Unit/CI checks |

Historical experiments и reports сохраняются для аудита. Их наличие не означает,
что они описывают текущую рекомендуемую команду или текущий статус.

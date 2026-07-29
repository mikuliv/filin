# Профили распространения

- `source-core` — одобренный собственный исходный код и документация, без образов, моделей, PCAP, Наборы данных, БД среды выполнения и секретов.
- `laboratory-source` — исходники лаборатории и декларации внешних ссылок, но не сами образы.
- `offline-third-party-bundle` — `not_approved`.
- `model-package` — `separate_license_required`.
- `dataset-package` — `separate_license_required`.

Профили являются allow/deny policy, а не готовыми архивами. Строгий validator запрещает требующий рассмотрение и исключённые типы в профилях одобренный.

Машинная область результата: `release_ready_scope=approved_source_profiles_only`. Одобрены ровно два профиля — `source-core` и `laboratory-source`; остальные три не готовы. `all_distribution_profiles_ready=false`.

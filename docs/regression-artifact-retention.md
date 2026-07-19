# Стандарт хранения regression-артефактов

v0.3.12.2 сохраняет в Git строгие manifests трёх bundles, а объёмные prediction, metrics, bootstrap и performance reports — только как воспроизводимые runtime-артефакты. Manifest отдельно фиксирует файловый hash источника episode mapping и canonical hash самого frozen mapping.

Каждый новый benchmark после v0.3.12.1 закрывается только вместе с полным, неизменяемым regression bundle. Manifest должен быть создан до prediction и содержать идентификатор этапа, SHA-256 протокола, кампании, исходного commit и dependency lock.

Обязательны frozen feature table с каноническими 51 признаками и их порядком, уникальные row ID, отдельные mappings для run, causal order и activity key, а также отдельные label table и episode mapping. Episode mapping создаётся до prediction; label table не может быть prediction input.

Bundle хранит capture manifest, идентификатор исторического кандидата, candidate manifest, immutable prediction, metric policy и policy result с версиями схем и SHA-256. Единственная runtime-копия без tracked manifest недопустима. PCAP или Zeek, из которых теоретически можно повторно извлечь признаки, не заменяют исходную frozen feature table.

Перед закрытием выполняется compatibility self-test: canonical 51-feature projection, уникальность и порядок строк, run/causal/activity mappings, отделение labels, episode mapping и hash-only readiness audit без model prediction. Неполный bundle получает `regression_bundle_complete: false` и не считается пригодным для научной regression-проверки.

Проверка выполняется командой:

```powershell
python tools/audit/validate_regression_bundle.py --manifest <path> --strict
```

`--metadata-only` разрешает инвентаризацию временно недоступных файлов, но никогда не подтверждает полноту bundle.

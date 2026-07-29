# Стандарт хранения артефактов регрессии

## Shadow подтверждающие материалы v0.3.14

Tracked остаются contract, policies, exporter, audits, tests и документация. Canonical events, spool, replay output, traces и reports являются только в среде выполнения и исключены из Git. Зафиксировано v0.3.13 используется только для чтения.

## Артефакты v0.3.13

В Git хранятся protocol, policies, код, тесты и документация. PCAP, Zeek logs, признак table, label vault, prediction, метрики и комплект подтверждающие материалы остаются ignored артефактами среды выполнения; их хеши связаны манифест и locks.

v0.3.12.2 сохраняет в Git строгие manifests трёх bundles, а объёмные prediction, показатели, bootstrap и performance reports — только как воспроизводимые артефакты среды выполнения. манифест отдельно фиксирует файловый hash источника episode mapping и canonical hash самого Зафиксировано mapping.

Каждый новый benchmark после v0.3.12.1 закрывается только вместе с полным, неизменяемым regression комплект. манифест должен быть создан до prediction и содержать идентификатор этапа, SHA-256 протокола, кампании, исходного Коммит и dependency lock.

Обязательны Зафиксировано признак table с каноническими 51 признаками и их порядком, уникальные row ID, отдельные mappings для run, causal order и activity key, а также отдельные label table и episode mapping. Episode mapping создаётся до prediction; label table не может быть prediction input.

комплект хранит capture манифест, идентификатор исторического кандидата, candidate манифест, immutable prediction, metric policy и policy result с версиями схем и SHA-256. Единственная копия среды выполнения без tracked манифест недопустима. PCAP или Zeek, из которых теоретически можно повторно извлечь признаки, не заменяют исходную Зафиксировано признак table.

Перед закрытием выполняется compatibility self-test: canonical 51-признак projection, уникальность и порядок строк, run/causal/activity mappings, отделение labels, episode mapping и hash-only readiness audit без модель prediction. Неполный комплект получает `regression_bundle_complete: false` и не считается пригодным для научной проверки регрессии.

Проверка выполняется командой:

```powershell
python tools/audit/validate_regression_bundle.py --manifest <path> --strict
```

`--metadata-only` разрешает инвентаризацию временно недоступных файлов, но никогда не подтверждает полноту комплект.

## Shadow trial v0.3.15

В Git сохраняются protocol, policies, aggregate scientific reports и комплект манифест. PCAP, Zeek logs, признак tables, label vault, row-level predictions/events, sink records, spool, checkpoints и resource traces остаются ignored среда выполнения artifacts. Их hashes фиксируются в tracked манифест.

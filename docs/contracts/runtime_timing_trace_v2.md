# Временная трасса runtime v2

`runtime_timing_trace_v2` — versioned контракт наблюдаемости для технических
испытаний staging transport. Он не изменяет event contract, state policy или
семантику доставки.

Каждая запись относится к одному логическому событию и содержит отдельные
идентификаторы транспортной попытки, batch, процесса, локального isolation
instance и clock domain. Поле `parent_trace_ref` задаёт причинное ребро, поэтому
параллельные ветви не превращаются в ложную линейную последовательность.

Обязательные поля определены JSON Schema
`rehearsal/contracts/runtime_timing_trace_v2.schema.json`:

- `trace_contract_version`;
- `event_id`, `trace_id`;
- `attempt_id`, `batch_id`;
- `component_id`, `process_instance_id`, `container_boot_id`;
- `clock_domain_id`;
- `timestamp_name`;
- `monotonic_ns`, `wall_clock_ns`;
- `parent_trace_ref`.

Разность monotonic timestamps допустимо вычислять только внутри общего
`clock_domain_id` либо при наличии замороженной attestation совместимости.
ACK наследует `attempt_id` и `batch_id` той попытки, которую он подтверждает.
После restart меняется boot identity; старые timestamps не переиспользуются.

Raw traces являются runtime-only evidence и не включаются в Git. В tracked
bundle входят только агрегированные проверки linkage, clock attestation и
latency.

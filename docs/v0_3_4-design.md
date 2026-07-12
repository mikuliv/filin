# v0.3.4 design boundary

`network_sensor_v0_3` is historical and remains unchanged for reproduction of
v0.3.1--v0.3.3. The future `network_sensor_v0_4` profile has one ordered source
of truth in `ml/features/schema.py` and is built only by the v0.4 builder.
Metadata, labels, markers, execution IDs, seeds, environment groups, and raw
endpoints are forbidden model features. The builder derives every feature from
assigned Zeek observations; no undeclared profile field is silently filled with
zero. Dataset quality audit rejects missing/unexpected fields and suspicious
constant or zero-only features.

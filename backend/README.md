# Backend status

`backend/` is a **HISTORICAL / DEMONSTRATION PROTOTYPE**, not a deployment
candidate. It does not load or serve the v0.3.1--v0.3.3 `network_sensor`
model. Its prediction confidence is heuristic and is not a calibrated ML
probability. The MITRE mapping is a static candidate, Sigma generation is a
draft, rule validation is not execution against Zeek or SIEM data, and
`matched_events` is not a result of a real search pipeline.

The v0.3.3 environment evaluation failed with benign recall `0.000`; ML
integration into this backend is prohibited until a future redesign campaign
and independent evaluation establish a new evidence base.

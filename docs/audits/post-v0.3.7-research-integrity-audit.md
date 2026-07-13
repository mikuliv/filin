# Post-v0.3.7 research-integrity audit

## 1. Scope

This audit reviews the repository state after the completed v0.3.7 research
stage. It compares documentation, code, manifests, policies, tests and the
available local runtime evidence. Historical results from v0.3.1 through
v0.3.7 are immutable: this work does not rerun holdout prediction, refit a
historical candidate, replace metrics, or modify a historical feature profile.

## 2. Repository state

- Audited base: `53773a991fd84d66cbe056979fe6182317a1ed03` on `main`.
- Latest completed stage: v0.3.7.
- Audit branch: `audit/post-v037-research-integrity`.
- Next free research-stage number observed in the repository: v0.3.8. This
  audit does not start or name a new training cycle.

## 3. Protected artifact boundary

PCAP, datasets, normalized events, reports, predictions and model binaries are
runtime artifacts excluded from Git. The audit used repository sources and
safe aggregate reads of locally available ignored datasets; it did not print
rows or copy protected artifacts into tracked paths. `FILIN_SECURE_ARTIFACT_ROOT`
was not configured during the initial audit. Checks that require that trusted
source therefore have status `not_executed_secure_artifacts_unavailable`.

The v0.3.7 frozen candidate manifest was already tracked at the audited base.
It is retained as immutable historical evidence. Future cycles must use the
external secure-artifact boundary and commit only a non-sensitive descriptor.

## 4. Confirmed findings

### RI-001 — silent one-second duration (critical)

- Evidence: `build_network_sensor_v4_dataset.py` reads an absent
  `actual_duration_seconds` field and falls back to `1.0`. Scenario execution
  records contain start/finish timestamps but do not populate that field.
  Safe aggregate inspection found 378/378 v0.3.4, 252/252 v0.3.6 and 1116/1116
  v0.3.7 v0.4 dataset rows equal to exactly one second.
- Affected versions: v0.3.4–v0.3.7.
- Historical metrics changed: no.
- Impact: duration-normalized rate features do not represent the marker-aligned
  sensor interval in those historical datasets.
- Correction: a new future-only profile requires a validated marker interval,
  permits validated actual timestamps only as secondary evidence, and has no
  numeric fallback.
- Verification: marker-duration, invalid-duration, rate and finite-input tests.
- Residual risk: historical metric impact cannot be quantified without a new
  protocol and training cycle; old holdouts must not be reopened as blind data.

### RI-002 — benign workflow names exceed behavior (high)

- Evidence: most v0.3.6/v0.3.7 `benign_*` identifiers reach a catch-all branch
  that emits the same bounded GET sequence.
- Affected versions: v0.3.6–v0.3.7.
- Historical metrics changed: no.
- Impact: claimed workflow diversity is greater than behavioral diversity.
- Correction: explicit future workflow plans with distinct HTTP, DNS, TCP and
  WebSocket actions and machine-checkable fingerprints.
- Verification: behavior-fingerprint, DNS-observation and WebSocket tests.
- Residual risk: unit fixtures do not replace an isolated runtime campaign.

### RI-003 — environment profiles are declarative only (high)

- Evidence: profiles declare latency, jitter, loss, reordering and topology
  conditions, but the campaign runner does not apply them; the v0.3.7
  condition audit returns literal success booleans.
- Affected versions: v0.3.6–v0.3.7.
- Historical metrics changed: no.
- Impact: condition-independence and environment-shift claims lack application
  evidence.
- Correction: future-only apply/verify/rollback controller with container-only
  safety guards and evidence records.
- Verification: fake-executor apply, verification, label-independence and
  rollback tests.
- Residual risk: real Docker/netem verification remains a manual local audit.

### RI-004 — ambiguous hashes and asserted integrity (high)

- Evidence: one holdout path derives `marker_interval_sha256` from execution
  mapping instead of marker intervals; several PCAP/event fields are ambiguous;
  multiple aggregation, condition, provenance and no-fit outcomes are literal
  booleans or zero counts rather than computed evidence.
- Affected versions: v0.3.5–v0.3.7.
- Historical metrics changed: no.
- Impact: historical reports cannot establish all claimed integrity properties.
- Correction: typed canonical hashes, tri-state evidence and a reproduction
  audit that compares independently recomputed aggregates.
- Verification: hash-domain, tri-state and reproduction mismatch tests.
- Residual risk: source-level fixes do not retroactively prove historical runs.

### RI-005 — integrity is absent from a final gate (high)

- Evidence: v0.3.6 calculates `passed` from metric/group/variant/stability
  checks only while separately emitting constant integrity flags. v0.3.5 and
  v0.3.7 runners cover only subsets of their YAML contracts.
- Affected versions: v0.3.5–v0.3.7.
- Historical metrics changed: no.
- Correction: a generic future policy evaluator requires exact YAML coverage,
  rejects `not_executed` as passed, and checks zero recall for every supported
  class.
- Verification: policy coverage, omitted-rule, tri-state and per-class tests.
- Residual risk: historical policy outcomes remain historical claims with the
  limitations above.

### RI-006 — misleading feature names (medium)

- Evidence: `orig_resp_bytes_ratio` and `orig_resp_packets_ratio` calculate the
  originator share of a total, not an originator-to-responder ratio.
- Affected versions: v0.3.4–v0.3.7 profiles that consume v0.4 aggregation.
- Historical metrics changed: no.
- Correction: the future profile uses `orig_bytes_share` and
  `orig_packets_share` and publishes a machine-readable feature dictionary.
- Verification: formula/name contract and ordered-profile tests.
- Residual risk: historical names remain unchanged for reproducibility.

### RI-007 — contradictory research status (medium)

- Evidence: README still identifies v0.3.3 as latest and the roadmap contains
  duplicate/outdated v0.3.3/v0.3.4 blocks despite completed v0.3.7 artifacts.
- Affected versions: current documentation.
- Historical metrics changed: no.
- Correction: `docs/research-state.yaml` becomes the authoritative status
  source and a validator checks critical prose claims.
- Verification: documentation consistency tests and CI validator.
- Residual risk: free-form prose still requires review outside validated claims.

## 5. Findings not reproduced

- No evidence was found that Git tracks PCAP, datasets, predictions, reports or
  model binaries at the audited base.
- Actual PCAP SHA-256 calculation already exists in sensor storage/preflight and
  in an older environment runner path. The defect is inconsistent adoption and
  ambiguous downstream naming, not universal absence of PCAP hashing.
- No historical holdout prediction or model fit was executed by this audit.

## 6. Checks blocked by unavailable secure artifacts

- Frozen candidate binary verification against an external manifest.
- Source-PCAP-to-normalized-events reproduction for all historical runs.
- Full Zeek output and marker interval hash reproduction.
- End-to-end aggregation comparison from protected normalized events.

These checks are not passed or failed. Their status is
`not_executed_secure_artifacts_unavailable` until an owner supplies a trusted
read-only `FILIN_SECURE_ARTIFACT_ROOT`.

## 7. Historical impact assessment

v0.3.4–v0.3.7 reports remain the record of what the historical code produced,
not a claim about corrected semantics. The duration defect directly affects
rate-feature interpretation. Workflow and condition defects weaken diversity
and independence claims. Constant integrity evidence weakens reproducibility
claims. None of those limitations authorizes retrospective replacement of
metrics. Corrected semantics require a new feature profile, new training data,
new candidate, new internal validation and a genuinely new prospective holdout.

## 8. Changes made

This section is finalized after implementation. Planned corrections are
future-only duration semantics, feature names and dictionary, explicit workflow
plans, environment evidence/rollback, typed hashes, tri-state integrity, policy
coverage, secure-artifact verification, research-state validation, tests and CI.

## 9. Tests executed

To be finalized after implementation.

## 10. Tests not executed

Protected runtime audits and a long Docker campaign are intentionally excluded
from automatic CI and remain not executed unless run manually with a trusted
secure-artifact root.

## 11. Remaining risks

- Historical reports contain asserted fields that cannot be upgraded into
  computed evidence after the fact.
- A fixture-driven environment-controller test cannot prove host kernel or
  Docker capability.
- The historical tracked v0.3.7 frozen manifest remains an exception to the
  future external-manifest policy.

## 12. Requirements for the next training cycle

Use new scenario/run IDs, seeds and a versioned profile; capture validated
marker intervals; apply and roll back recorded environment conditions; build a
new dataset; fit a new candidate without v0.3.6/v0.3.7 holdout tuning; freeze
artifact, schema, policy and integrity evidence before validation; require full
policy coverage and no zero-recall supported class.

## 13. Requirements for the next prospective holdout

Use an unseen, pre-registered catalog and protocol after candidate freeze. Lock
source hashes, row order and execution mapping before the only prediction pass.
Disallow fit, calibration, threshold tuning, feature selection, row exclusion,
metric-driven reruns and resume-time repeated prediction. Keep artifacts in the
secure root and publish only non-sensitive aggregate evidence.

# Roadmap

The machine-readable authority for current status is
[`research-state.yaml`](research-state.yaml).

## Completed research stages

- v0.3.1 — baseline evaluation.
- v0.3.2 — frozen robustness evaluation.
- v0.3.3 — negative environment evaluation; benign recall `0.000` and false
  positive rate `1.000` in that historical protocol.
- v0.3.4 — benign representation redesign, grouped internal validation and
  candidate freeze.
- v0.3.5 — frozen regression evaluation on a known historical benchmark; not a
  blind prospective holdout.
- v0.3.6 — prospective holdout completed with policy not passed; historical
  result is immutable and may not be reopened for tuning.
- v0.3.7 — new hierarchical training/internal-validation cycle completed with
  frozen internal-validation policy not passed.

## Active work

The post-v0.3.7 research-integrity audit records historical limitations and
implements future-only corrections. It does not alter historical metrics,
rerun holdout prediction or correct the v0.3.7 candidate retrospectively.

## Next allowed stage

The next free version is v0.3.8. Because duration semantics, benign workflows,
environment application, feature semantics and integrity gates changed, the
only allowed use is a new training cycle with new runs, scenario IDs, seeds,
feature profile, candidate freeze and internal validation. v0.3.6 and v0.3.7
must not be presented as a new blind holdout or used for hidden tuning.

A later prospective holdout requires a separately pre-registered protocol,
unseen scenarios and a single prediction after candidate and policy freeze.
Backend integration and shadow mode remain prohibited until an applicable
future policy explicitly passes. Production readiness is not established.

## Longer-term work

Independent-infrastructure validation, encrypted-traffic observability,
online inference, analyst workflow, SIEM integration and response actions are
future research. Active response and automatic blocking are out of scope.

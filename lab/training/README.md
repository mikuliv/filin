# v0.3.4 training stage

The stage validates the data-access policy before any campaign execution. It
must never load v0.3.3 feature rows or labels for fit, model selection, CV, or
threshold tuning. Internal validation is separate and permitted only after the
candidate freeze. v0.3.3 remains locked for future v0.3.5 regression work.

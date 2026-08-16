# Network validation operational contract completion

## Status

The predecessor Phase 1 execution package remains immutable and historically valid. It is
superseded only for operational initialization because its mapping and ledger contracts did
not fully specify physical serialization, fingerprinting, ledger genesis, or an atomic
package-bound initialization state.

The versioned operational contracts complete those details without changing the scientific
protocol. The 288 scenario templates, three repetitions, 864 execution units, scientific
seeds, exact execution order, split, stress views, counterfactual pairs, acceptance criteria,
feature contract and order, image identities, timing, and retry/replacement/exclusion
scientific semantics remain fixed by their existing artifacts.

## Boundary

Contract completion and superseding-package construction do not perform campaign
initialization. No mapping secret, secret metadata, campaign ledger, initialization manifest,
mapping entry, label, PCAP, scientific session, model, prediction, or metric is created.

The superseding package requires a new package-specific output root and a new campaign-level
runtime preflight. The empty output root prepared for the predecessor package is not reused.
Only a later, separately authorized initialization operation may create the external secret
and zero-record control artifacts under the completed contracts.

## Validation

The operational audit validates exact HMAC-SHA256 input and key rules, raw secret bytes and
fingerprinting, storage and ACL policy, zero-byte JSON Lines ledger state, canonical record
digests, genesis and chain rules, package binding, initialization-manifest self-digest,
fail-closed installation order, rollback scope, and no-overwrite idempotence.

Scientific equivalence validation compares the superseding package inputs with the immutable
predecessor package, superseding freeze, and exact Phase 1 run plan. Any digest, unit identity,
seed, count, proxy-warning, nuisance-warning, or counterfactual-pair drift blocks package
creation.

# Candidate lineage

Candidate lineage связывает artifact, manifest, feature contract, state policy,
calibration/conformal metadata и event compatibility.

Current frozen candidate — `v03154:65a3dd912d845bc1`. Он создан на development
этапе v0.3.15.4, проверен independent scientific holdout v0.3.15.5 и получил
runtime-compatible event path в v0.3.15.5.1.

External dataset в режиме `authorized_development` должен создавать новую
lineage. Он не может одновременно подтверждать current candidate как blind
holdout. Registry и candidate manifest являются machine-readable источниками
identity.

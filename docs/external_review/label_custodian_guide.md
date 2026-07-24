# Руководство label custodian

Custodian хранит labels отдельно, фиксирует их canonical commitment до blind
handoff и не меняет после commitment. Labels раскрываются только при наличии
валидного prediction commitment. Reveal должен точно совпасть с первоначальным
label hash; mismatch немедленно invalidates trial.

# Эксперимент v0.3.8

Этап реализует новый training/internal-validation cycle для class-conditional uncertainty, conformal prediction, support и episode evidence. Источники v0.3.6 и v0.3.7 защищены и не используются для обучения или настройки.

## Порядок исполнения

1. protocol/data/campaign manifests и feature contract фиксируются до training;
2. 12 training runs проходят capability, integrity и independence audits;
3. nested grouped OOF выбирает архитектуру и все thresholds;
4. `frozen_candidate_manifest.yaml` создаётся до validation collection;
5. после 6 validation runs создаётся `validation_lock_manifest.yaml`;
6. frozen candidate один раз выполняет no-fit prediction и policy evaluation.

Выбран contextual control из 51 признака, HGB gate/subtype, group-aware sigmoid calibration, Mondrian `alpha=0.05`, class-conditional 3-NN support с квантилем `0.975` и `consistent_2_of_3`. Closed-set macro F1 `0.990734`, FPR `0`, episode recall `0.933333`, unresolved rate `0.066667`. Window и episode gates не пройдены, поэтому `v0_3_8_policy_passed=false`, `ready_for_v0_3_9=false`; backend и shadow mode запрещены.

Runtime datasets, models, predictions и подробные reports исключены из Git. Коммитятся только код, policies и frozen source manifests с контрольными суммами.

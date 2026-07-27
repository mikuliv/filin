---
doc_schema: filin_document_v2
title: Инвентаризация документации v2
document_type: audit
audience:
  - auditor
lifecycle: generated
authoritative_for: []
source_of_truth:
  - git ls-files '*.md'
  - docs/audit/documentation_inventory_v2.json
last_reviewed_stage: v0.4.4
generated: true
evidence_immutable: false
---

# Инвентаризация документации v2

> Генератор: `tools/docs/build_documentation_inventory.py`. Команда: `python -m tools.docs.build_documentation_inventory`. Генерируемую область вручную не редактировать.

<!-- generated:start -->
## Сводка

- Документов: **261**.
- Защищённых: **61**.
- Текущих: **176**.
- Исторических и frozen: **85**.
- Созданных: **43**; переписанных: **49**; redirects: **15**.
- Сломанных ссылок: **0**; anchors: **0**.

## Документы

| Путь | Категория | Жизненный цикл | Текущий/исторический | Protected | Действие | SHA до | SHA после |
|---|---|---|---|---:|---|---|---|
| `README.md` | Авторитетный текущий документ | `current` | current | нет | `rewritten` | `ddd35d59e515` | `e4ad7c0326b8` |
| `backend/README.md` | Текущий справочный документ | `current` | current | нет | `unchanged` | `587348d47eed` | `587348d47eed` |
| `collectors/README.md` | Текущий справочный документ | `current` | current | нет | `rewritten` | `5e169f7419f1` | `d5f6fa75eb7f` |
| `collectors/csv_collector/README.md` | Текущий справочный документ | `current` | current | нет | `rewritten` | `075e999d885f` | `5b5767c662db` |
| `collectors/suricata_collector/README.md` | Текущий справочный документ | `current` | current | нет | `rewritten` | `614d3bf41069` | `e916dea343e2` |
| `collectors/zeek_collector/README.md` | Текущий справочный документ | `current` | current | нет | `rewritten` | `aa0ba175d33d` | `f2d023f84636` |
| `datasets/README.md` | Текущий справочный документ | `current` | current | нет | `rewritten` | `181726a5f8d5` | `75b0e7648a0c` |
| `docs/architecture.md` | Redirect-документ | `redirect` | current | нет | `redirected` | `14c0df26c5bc` | `99b7814f3165` |
| `docs/architecture/component-map.md` | Авторитетный текущий документ | `current` | current | нет | `created` | `—` | `a4eff5235218` |
| `docs/architecture/controlled_local_rehearsal_v0_3_17.md` | Текущий справочный документ | `current` | current | нет | `unchanged` | `6ada20e86b28` | `6ada20e86b28` |
| `docs/architecture/current-vs-historical.md` | Авторитетный текущий документ | `current` | current | нет | `created` | `—` | `247bf1d1ab48` |
| `docs/architecture/data-flow.md` | Текущий справочный документ | `current` | current | нет | `unchanged` | `8d723bfca934` | `8d723bfca934` |
| `docs/architecture/delivery-runtime.md` | Текущий справочный документ | `current` | current | нет | `unchanged` | `74817c93b058` | `74817c93b058` |
| `docs/architecture/detection-and-runtime-track.md` | Авторитетный текущий документ | `current` | current | нет | `created` | `—` | `02271c838d4f` |
| `docs/architecture/detection-pipeline.md` | Текущий справочный документ | `current` | current | нет | `unchanged` | `ceb4f5ee4f36` | `ceb4f5ee4f36` |
| `docs/architecture/end-to-end-data-flow.md` | Авторитетный текущий документ | `current` | current | нет | `created` | `—` | `f67a85cf8804` |
| `docs/architecture/index.md` | Авторитетный текущий документ | `current` | current | нет | `rewritten` | `3768ca49483c` | `870f81fa90b6` |
| `docs/architecture/laboratory-console.md` | Авторитетный текущий документ | `current` | current | нет | `created` | `—` | `d9941307a14b` |
| `docs/architecture/limitations.md` | Авторитетный текущий документ | `current` | current | нет | `rewritten` | `970199f46ebd` | `cdc9087c10e5` |
| `docs/architecture/overview.md` | Авторитетный текущий документ | `current` | current | нет | `rewritten` | `6e36c710a231` | `eb28d0cae077` |
| `docs/architecture/passive-events.md` | Текущий справочный документ | `current` | current | нет | `unchanged` | `6447c0c8a8e9` | `6447c0c8a8e9` |
| `docs/architecture/reconstruction-and-analysis-track.md` | Авторитетный текущий документ | `current` | current | нет | `created` | `—` | `71a6abafa7ec` |
| `docs/architecture/staging_connector_v0_3_16.md` | Текущий справочный документ | `current` | current | нет | `unchanged` | `3522b1cc4862` | `3522b1cc4862` |
| `docs/architecture/stateful-processing.md` | Текущий справочный документ | `current` | current | нет | `unchanged` | `7df138cf8a1a` | `7df138cf8a1a` |
| `docs/architecture/storage-and-artifacts.md` | Авторитетный текущий документ | `current` | current | нет | `created` | `—` | `ad149485cfc2` |
| `docs/architecture/trust-boundaries.md` | Авторитетный текущий документ | `current` | current | нет | `rewritten` | `b9435321c3ed` | `1f133afa2697` |
| `docs/audit/documentation_inventory.md` | Redirect-документ | `redirect` | current | нет | `redirected` | `eaef0e2d241d` | `c23a3c126926` |
| `docs/audit/documentation_inventory_v2.md` | Генерируемый индекс или представление | `generated` | current | нет | `created` | `—` | `28b7cdcdbae0` |
| `docs/audit/documentation_navigation_acceptance_v2.md` | Текущий справочный документ | `current` | current | нет | `created` | `—` | `1839146eb403` |
| `docs/audit/documentation_path_migration_v2.md` | Текущий справочный документ | `current` | current | нет | `created` | `—` | `cb437745bba4` |
| `docs/audit/documentation_refactor_plan_v2.md` | Текущий справочный документ | `current` | current | нет | `created` | `—` | `8ca9d2c1f48b` |
| `docs/audit/documentation_refactor_report.md` | Redirect-документ | `redirect` | current | нет | `redirected` | `9560552f9edb` | `189bcd7002c2` |
| `docs/audit/documentation_refactor_report_v2.md` | Текущий справочный документ | `current` | current | нет | `created` | `—` | `a44ebfe2a87b` |
| `docs/audit/index.md` | Авторитетный текущий документ | `current` | current | нет | `created` | `—` | `226085a3a2b6` |
| `docs/audits/post-v0.3.7-research-integrity-audit.md` | Текущий справочный документ | `current` | current | нет | `unchanged` | `67a8d0b18427` | `67a8d0b18427` |
| `docs/audits/pre-v0.3.8-runtime-integrity-acceptance.md` | Текущий справочный документ | `current` | current | нет | `unchanged` | `5a22a9de0523` | `5a22a9de0523` |
| `docs/code-origin-audit.md` | Текущий справочный документ | `current` | current | нет | `unchanged` | `556db0491996` | `556db0491996` |
| `docs/contracts/connector_ingress_ack_v1.md` | Текущий справочный документ | `current` | current | нет | `unchanged` | `ac3174d6e452` | `ac3174d6e452` |
| `docs/contracts/connector_ingress_v1.md` | Текущий справочный документ | `current` | current | нет | `unchanged` | `d47c2c1c4ace` | `d47c2c1c4ace` |
| `docs/contracts/index.md` | Генерируемый индекс или представление | `generated` | current | нет | `rewritten` | `a6c911719a75` | `3baa92ef57bd` |
| `docs/contracts/operator_projection_v1.md` | Текущий справочный документ | `current` | current | нет | `unchanged` | `f986ab48a46f` | `f986ab48a46f` |
| `docs/contracts/receiver_batch_ack_v1.md` | Текущий справочный документ | `current` | current | нет | `unchanged` | `d5df61679a88` | `d5df61679a88` |
| `docs/contracts/rehearsal_observability_v1.md` | Текущий справочный документ | `current` | current | нет | `unchanged` | `c8ca814fb2b0` | `c8ca814fb2b0` |
| `docs/contracts/runtime_timing_trace_v2.md` | Frozen evidence | `frozen` | historical | да | `unchanged` | `c76cf47dbc3b` | `c76cf47dbc3b` |
| `docs/contracts/shadow-backend-gap-analysis.md` | Текущий справочный документ | `current` | current | нет | `unchanged` | `27768cc25ad2` | `27768cc25ad2` |
| `docs/contracts/shadow-event-v1.md` | Текущий справочный документ | `current` | current | нет | `unchanged` | `2420791e11b7` | `2420791e11b7` |
| `docs/contracts/shadow-event-v2.md` | Текущий справочный документ | `current` | current | нет | `unchanged` | `8bd470523529` | `8bd470523529` |
| `docs/contracts/shadow-trial-runtime.md` | Текущий справочный документ | `current` | current | нет | `unchanged` | `fe85e3533616` | `fe85e3533616` |
| `docs/contracts/staging_event_batch_v1.md` | Текущий справочный документ | `current` | current | нет | `unchanged` | `fb87f685caf2` | `fb87f685caf2` |
| `docs/contributing/adding-a-contract.md` | Руководство разработчика | `current` | current | нет | `created` | `—` | `cd4a8db342c5` |
| `docs/contributing/adding-a-report.md` | Руководство разработчика | `current` | current | нет | `created` | `—` | `80da3a7ec9ee` |
| `docs/contributing/adding-a-stage.md` | Руководство разработчика | `current` | current | нет | `created` | `—` | `7735dace0900` |
| `docs/contributing/adding-a-subsystem-readme.md` | Руководство разработчика | `current` | current | нет | `created` | `—` | `0e19a730e33d` |
| `docs/contributing/documentation-maintenance.md` | Руководство разработчика | `current` | current | нет | `created` | `—` | `3e718d6980ea` |
| `docs/contributing/documentation-style.md` | Руководство разработчика | `current` | current | нет | `rewritten` | `ad467b47bd2b` | `3a16051145ea` |
| `docs/contributing/testing-and-validation.md` | Руководство разработчика | `current` | current | нет | `rewritten` | `1fd32af5212d` | `7ac07868969d` |
| `docs/current-capabilities.md` | Redirect-документ | `redirect` | current | нет | `redirected` | `156f26635950` | `fdcb6eb5e4de` |
| `docs/data-provenance.md` | Текущий справочный документ | `current` | current | нет | `unchanged` | `926f7151195c` | `926f7151195c` |
| `docs/dependency-licenses.md` | Текущий справочный документ | `current` | current | нет | `unchanged` | `0d5241dc17e6` | `0d5241dc17e6` |
| `docs/development-history.md` | Redirect-документ | `redirect` | current | нет | `redirected` | `57edc82d9764` | `ae900178e9e0` |
| `docs/documentation-policy.md` | Redirect-документ | `redirect` | current | нет | `redirected` | `d538c950bc52` | `5d914857e8da` |
| `docs/experiments.md` | Авторитетный текущий документ | `current` | current | нет | `rewritten` | `e1d83c9eb96a` | `93fdd697b8a4` |
| `docs/experiments/v0_3_11.md` | Историческое описание | `historical` | historical | нет | `unchanged` | `b221582a5002` | `b221582a5002` |
| `docs/experiments/v0_3_12.md` | Историческое описание | `historical` | historical | нет | `unchanged` | `22d19e14b43d` | `22d19e14b43d` |
| `docs/experiments/v0_3_12_1.md` | Историческое описание | `historical` | historical | нет | `unchanged` | `49e49c8c9975` | `49e49c8c9975` |
| `docs/experiments/v0_3_12_2.md` | Историческое описание | `historical` | historical | нет | `unchanged` | `879a1ac91431` | `879a1ac91431` |
| `docs/experiments/v0_3_13.md` | Историческое описание | `historical` | historical | нет | `unchanged` | `ddc5324121d7` | `ddc5324121d7` |
| `docs/experiments/v0_3_14.md` | Историческое описание | `historical` | historical | нет | `unchanged` | `66ce264ab5bc` | `66ce264ab5bc` |
| `docs/experiments/v0_3_14_errata.md` | Историческое описание | `historical` | historical | нет | `unchanged` | `80ac701f232d` | `80ac701f232d` |
| `docs/experiments/v0_3_15.md` | Историческое описание | `historical` | historical | нет | `unchanged` | `7505eee9ab6a` | `7505eee9ab6a` |
| `docs/experiments/v0_3_15_1.md` | Историческое описание | `historical` | historical | нет | `unchanged` | `8b766da2ce30` | `8b766da2ce30` |
| `docs/experiments/v0_3_15_2.md` | Историческое описание | `historical` | historical | нет | `unchanged` | `52ccd2d834ce` | `52ccd2d834ce` |
| `docs/experiments/v0_3_15_3.md` | Frozen evidence | `frozen` | historical | да | `unchanged` | `94e59593e833` | `94e59593e833` |
| `docs/experiments/v0_3_15_4.md` | Frozen evidence | `frozen` | historical | да | `unchanged` | `c90c0bd13468` | `c90c0bd13468` |
| `docs/experiments/v0_3_15_4_proposed.md` | Историческое описание | `historical` | historical | нет | `unchanged` | `2cada57bd8b4` | `2cada57bd8b4` |
| `docs/experiments/v0_3_15_5.md` | Frozen evidence | `frozen` | historical | да | `unchanged` | `b55046151e6c` | `b55046151e6c` |
| `docs/experiments/v0_3_15_5_1.md` | Историческое описание | `historical` | historical | нет | `unchanged` | `9825b1d7d015` | `9825b1d7d015` |
| `docs/experiments/v0_3_16.md` | Историческое описание | `historical` | historical | нет | `unchanged` | `0bef19870b13` | `0bef19870b13` |
| `docs/experiments/v0_3_17.md` | Историческое описание | `historical` | historical | нет | `unchanged` | `037a55ebcfb5` | `037a55ebcfb5` |
| `docs/experiments/v0_3_17_1.md` | Frozen evidence | `frozen` | historical | да | `unchanged` | `9bbd90302dff` | `9bbd90302dff` |
| `docs/experiments/v0_3_18.md` | Frozen evidence | `frozen` | historical | да | `unchanged` | `4fdceb4b3bc7` | `4fdceb4b3bc7` |
| `docs/experiments/v0_4_0.md` | Frozen evidence | `frozen` | historical | да | `unchanged` | `42106953dd41` | `42106953dd41` |
| `docs/experiments/v0_4_1.md` | Frozen evidence | `frozen` | historical | да | `unchanged` | `6df371878d28` | `6df371878d28` |
| `docs/experiments/v0_4_2.md` | Frozen evidence | `frozen` | historical | да | `unchanged` | `192516bc340b` | `192516bc340b` |
| `docs/experiments/v0_4_3.md` | Frozen evidence | `frozen` | historical | да | `unchanged` | `4e09a0bc2f7a` | `4e09a0bc2f7a` |
| `docs/experiments/v0_4_3_1.md` | Историческое описание | `historical` | historical | нет | `unchanged` | `f925636f9a32` | `f925636f9a32` |
| `docs/external_review/README.md` | Frozen evidence | `frozen` | historical | да | `unchanged` | `967b22acd235` | `967b22acd235` |
| `docs/external_review/architecture.md` | Frozen evidence | `frozen` | historical | да | `unchanged` | `bf8aeb0b339b` | `bf8aeb0b339b` |
| `docs/external_review/confirmed_scope.md` | Frozen evidence | `frozen` | historical | да | `unchanged` | `a5609b0032c1` | `a5609b0032c1` |
| `docs/external_review/data_acceptance_policy.md` | Frozen evidence | `frozen` | historical | да | `unchanged` | `5db96299691d` | `5db96299691d` |
| `docs/external_review/data_provider_guide.md` | Frozen evidence | `frozen` | historical | да | `unchanged` | `f21e697f9f04` | `f21e697f9f04` |
| `docs/external_review/data_transfer_requirements.md` | Frozen evidence | `frozen` | historical | да | `unchanged` | `a106607a806b` | `a106607a806b` |
| `docs/external_review/evaluator_guide.md` | Frozen evidence | `frozen` | historical | да | `unchanged` | `fd6820956c91` | `fd6820956c91` |
| `docs/external_review/known_limitations.md` | Frozen evidence | `frozen` | historical | да | `unchanged` | `b429b48129a1` | `b429b48129a1` |
| `docs/external_review/label_custodian_guide.md` | Frozen evidence | `frozen` | historical | да | `unchanged` | `6bf62c3172af` | `6bf62c3172af` |
| `docs/external_review/legal_requirements_checklist.md` | Frozen evidence | `frozen` | historical | да | `unchanged` | `16cfa062c3e5` | `16cfa062c3e5` |
| `docs/external_review/metric_policy.md` | Frozen evidence | `frozen` | historical | да | `unchanged` | `65a73841e703` | `65a73841e703` |
| `docs/external_review/publication_requirements.md` | Frozen evidence | `frozen` | historical | да | `unchanged` | `24bf97ca88d6` | `24bf97ca88d6` |
| `docs/external_review/reproducibility_guide.md` | Frozen evidence | `frozen` | historical | да | `unchanged` | `8b75532dd080` | `8b75532dd080` |
| `docs/external_review/result_approver_guide.md` | Frozen evidence | `frozen` | historical | да | `unchanged` | `434e10a4ca6b` | `434e10a4ca6b` |
| `docs/external_review/retention_and_deletion_requirements.md` | Frozen evidence | `frozen` | historical | да | `unchanged` | `b7cacd0a881c` | `b7cacd0a881c` |
| `docs/external_review/reviewer_guide.md` | Frozen evidence | `frozen` | historical | да | `unchanged` | `2a9db82098e3` | `2a9db82098e3` |
| `docs/external_review/stop_conditions.md` | Frozen evidence | `frozen` | historical | да | `unchanged` | `c0902c170b52` | `c0902c170b52` |
| `docs/external_review/trial_operator_guide.md` | Frozen evidence | `frozen` | historical | да | `unchanged` | `f812f2806bd3` | `f812f2806bd3` |
| `docs/getting-started/auditor-entrypoint.md` | Руководство разработчика | `current` | current | нет | `created` | `—` | `039cc45834c9` |
| `docs/getting-started/developer-entrypoint.md` | Руководство разработчика | `current` | current | нет | `created` | `—` | `30aaadc45d33` |
| `docs/getting-started/external-review-entrypoint.md` | Руководство разработчика | `current` | current | нет | `created` | `—` | `a1a3ddc40412` |
| `docs/getting-started/laboratory-console.md` | Руководство пользователя или оператора | `current` | current | нет | `rewritten` | `711256dd221b` | `4795e69d40ea` |
| `docs/getting-started/local-environment.md` | Руководство разработчика | `current` | current | нет | `rewritten` | `0050fed25317` | `14ef0667f4ce` |
| `docs/getting-started/overview.md` | Текущий справочный документ | `current` | current | нет | `rewritten` | `e0aa2d33ce67` | `45997f9fcf82` |
| `docs/getting-started/repository-layout.md` | Авторитетный текущий документ | `current` | current | нет | `rewritten` | `910ec72c4e30` | `308d87c07b87` |
| `docs/getting-started/reviewing-laboratory-cards.md` | Руководство пользователя или оператора | `current` | current | нет | `rewritten` | `1a50718bdb21` | `8ed1c9d37795` |
| `docs/getting-started/testing.md` | Руководство разработчика | `current` | current | нет | `rewritten` | `553acb3c502e` | `c6f8558576d2` |
| `docs/getting-started/troubleshooting.md` | Руководство пользователя или оператора | `current` | current | нет | `created` | `—` | `a25d8e0de03e` |
| `docs/glossary.md` | Redirect-документ | `redirect` | current | нет | `redirected` | `9be4e54790f7` | `a78b99a74996` |
| `docs/history/archived-documentation.md` | Историческое описание | `historical` | historical | нет | `rewritten` | `4d63ef9ba30e` | `f74d52af14c1` |
| `docs/history/corrections-and-negative-results.md` | Историческое описание | `historical` | historical | нет | `rewritten` | `62926dd3ebcc` | `c01ed84633fc` |
| `docs/history/historical-backend.md` | Историческое описание | `historical` | historical | нет | `created` | `—` | `af48b4da1331` |
| `docs/history/historical-limitations.md` | Историческое описание | `historical` | historical | нет | `created` | `—` | `d025a0e5be20` |
| `docs/history/historical-mitre-and-sigma.md` | Историческое описание | `historical` | historical | нет | `created` | `—` | `c626fdbab236` |
| `docs/history/historical-modeling.md` | Историческое описание | `historical` | historical | нет | `created` | `—` | `32bff8df1bf8` |
| `docs/history/index.md` | Историческое описание | `current` | current | нет | `created` | `—` | `2fa443d0ca0f` |
| `docs/history/stage-timeline.md` | Историческое описание | `historical` | historical | нет | `rewritten` | `59360f30bf8e` | `6f1f9b74b1ed` |
| `docs/incident-workflow.md` | Redirect-документ | `redirect` | current | нет | `redirected` | `ab4754007f6c` | `a3b0759c9e55` |
| `docs/index.md` | Авторитетный текущий документ | `current` | current | нет | `rewritten` | `bdbd2ff6c23d` | `0b1ee4647b46` |
| `docs/lab-stand.md` | Текущий справочный документ | `current` | current | нет | `unchanged` | `120d0c073442` | `120d0c073442` |
| `docs/licensing-audit.md` | Текущий справочный документ | `current` | current | нет | `unchanged` | `6864b690a437` | `6864b690a437` |
| `docs/limitations.md` | Redirect-документ | `redirect` | current | нет | `redirected` | `df01a16cec0a` | `f88e43119901` |
| `docs/methodology/index.md` | Текущий справочный документ | `current` | current | нет | `unchanged` | `86988c7c7bb0` | `86988c7c7bb0` |
| `docs/mitre-mapping.md` | Redirect-документ | `redirect` | current | нет | `redirected` | `831103c32a2f` | `5a7c82167d5d` |
| `docs/modeling.md` | Redirect-документ | `redirect` | current | нет | `redirected` | `f2f82a3ff135` | `df9810a06e92` |
| `docs/operations/index.md` | Текущий справочный документ | `current` | current | нет | `unchanged` | `a183278b8726` | `a183278b8726` |
| `docs/operations/local_rehearsal_recovery_runbook.md` | Текущий справочный документ | `current` | current | нет | `unchanged` | `e8747f7757a8` | `e8747f7757a8` |
| `docs/operations/local_rehearsal_runbook.md` | Текущий справочный документ | `current` | current | нет | `unchanged` | `e5ee5f41b504` | `e5ee5f41b504` |
| `docs/operations/reference_receiver_runbook.md` | Текущий справочный документ | `current` | current | нет | `unchanged` | `cf5fd2b5df35` | `cf5fd2b5df35` |
| `docs/performance.md` | Текущий справочный документ | `current` | current | нет | `unchanged` | `3a0b689cce36` | `3a0b689cce36` |
| `docs/post-migration-technical-status.md` | Текущий справочный документ | `current` | current | нет | `unchanged` | `cdfa5fbfc4a7` | `cdfa5fbfc4a7` |
| `docs/protocols/index.md` | Генерируемый индекс или представление | `generated` | current | нет | `rewritten` | `4ed068ecfcff` | `00317fb682c4` |
| `docs/reference/artifact-types.md` | Текущий справочный документ | `current` | current | нет | `created` | `—` | `75ad30ec7680` |
| `docs/reference/command-reference.md` | Авторитетный текущий документ | `current` | current | нет | `created` | `—` | `62e414747098` |
| `docs/reference/component-directory.md` | Авторитетный текущий документ | `current` | current | нет | `created` | `—` | `9efe0bba46e1` |
| `docs/reference/document-lifecycle.md` | Авторитетный текущий документ | `current` | current | нет | `created` | `—` | `c8eec52b02cd` |
| `docs/reference/error-and-result-codes.md` | Текущий справочный документ | `current` | current | нет | `created` | `—` | `f7bc75a4ccee` |
| `docs/reference/glossary.md` | Авторитетный текущий документ | `current` | current | нет | `created` | `—` | `7db69be6b617` |
| `docs/reference/sources-of-truth.md` | Авторитетный текущий документ | `current` | current | нет | `created` | `—` | `648da8c02c46` |
| `docs/reference/status-values.md` | Текущий справочный документ | `current` | current | нет | `created` | `—` | `5c9445daa0af` |
| `docs/reference/terminology.md` | Авторитетный текущий документ | `current` | current | нет | `created` | `—` | `420c70d80b52` |
| `docs/regression-artifact-retention.md` | Текущий справочный документ | `current` | current | нет | `unchanged` | `7d6ddf4f5b99` | `7d6ddf4f5b99` |
| `docs/reports/index.md` | Генерируемый индекс или представление | `generated` | current | нет | `rewritten` | `a92289f35c01` | `f493cadaf5ee` |
| `docs/repository-migration.md` | Текущий справочный документ | `current` | current | нет | `unchanged` | `a894073ac386` | `a894073ac386` |
| `docs/repository-separation-plan.md` | Текущий справочный документ | `current` | current | нет | `unchanged` | `e139b5a1fd74` | `e139b5a1fd74` |
| `docs/reproducibility.md` | Redirect-документ | `redirect` | current | нет | `redirected` | `4ac24be34e4e` | `6db6e3b8dca6` |
| `docs/research/candidate-lineage.md` | Авторитетный текущий документ | `current` | current | нет | `rewritten` | `5f46d117410b` | `330c0afd423f` |
| `docs/research/causal-features.md` | Текущий справочный документ | `current` | current | нет | `rewritten` | `41694527c0ea` | `de97ff8907f9` |
| `docs/research/competing-hypotheses.md` | Frozen evidence | `frozen` | historical | да | `unchanged` | `11f699cb1309` | `11f699cb1309` |
| `docs/research/evaluation-principles.md` | Текущий справочный документ | `current` | current | нет | `rewritten` | `9e1097f88cd2` | `c7d76ac336c1` |
| `docs/research/incident-reconstruction.md` | Frozen evidence | `frozen` | historical | да | `unchanged` | `04b4a054d724` | `04b4a054d724` |
| `docs/research/laboratory-case-catalog.md` | Авторитетный текущий документ | `current` | current | нет | `created` | `—` | `d7041a31caac` |
| `docs/research/laboratory-console-ui.md` | Redirect-документ | `redirect` | current | нет | `redirected` | `a4f22d361453` | `f1ed3f37ecc0` |
| `docs/research/laboratory-console.md` | Frozen evidence | `frozen` | historical | да | `unchanged` | `6b55dfe93a0f` | `6b55dfe93a0f` |
| `docs/research/manual-incident-review.md` | Frozen evidence | `frozen` | historical | да | `unchanged` | `1a8b57ad68e2` | `1a8b57ad68e2` |
| `docs/research/methodology.md` | Авторитетный текущий документ | `current` | current | нет | `rewritten` | `1cc2064ced82` | `36a7694bfc9d` |
| `docs/research/operator-incident-workflow.md` | Авторитетный текущий документ | `current` | current | нет | `created` | `—` | `a86ca161448d` |
| `docs/research/reproducibility.md` | Авторитетный текущий документ | `current` | current | нет | `rewritten` | `78c8f06924b8` | `955a99dedc74` |
| `docs/research/temporal-reconstruction.md` | Frozen evidence | `frozen` | historical | да | `unchanged` | `8b2d805c7549` | `8b2d805c7549` |
| `docs/research/uncertainty-and-abstention.md` | Текущий справочный документ | `current` | current | нет | `rewritten` | `2fc89b0f0424` | `87d1e28d0835` |
| `docs/roadmap.md` | Текущий справочный документ | `current` | current | нет | `rewritten` | `86683fa36c3b` | `6316b247fd5f` |
| `docs/safety-model.md` | Текущий справочный документ | `current` | current | нет | `unchanged` | `378a0c085693` | `378a0c085693` |
| `docs/security/index.md` | Текущий справочный документ | `current` | current | нет | `unchanged` | `e141d7e5c02d` | `e141d7e5c02d` |
| `docs/security/staging_transport_security_v1.md` | Текущий справочный документ | `current` | current | нет | `unchanged` | `8fee3f85af21` | `8fee3f85af21` |
| `docs/sigma-generation.md` | Redirect-документ | `redirect` | current | нет | `redirected` | `75d6ffab94c0` | `6256510bbfad` |
| `docs/status.md` | Redirect-документ | `redirect` | current | нет | `redirected` | `306d9f405f33` | `50da05fd05a6` |
| `docs/status/confirmed-capabilities.md` | Авторитетный текущий документ | `current` | current | нет | `rewritten` | `f8085e10f3da` | `4598defaa5df` |
| `docs/status/current-status.md` | Авторитетный текущий документ | `current` | current | нет | `rewritten` | `2062630b3897` | `6496f275100e` |
| `docs/status/documentation_refactor_handoff.md` | Текущий справочный документ | `current` | current | нет | `unchanged` | `c4ed023f005e` | `c4ed023f005e` |
| `docs/status/laboratory-track-history.md` | Текущий справочный документ | `current` | current | нет | `created` | `—` | `272725af51b8` |
| `docs/status/mainline-history.md` | Текущий справочный документ | `current` | current | нет | `created` | `—` | `e640e4dc97a3` |
| `docs/status/next-stage.md` | Авторитетный текущий документ | `current` | current | нет | `rewritten` | `b035bbb425ca` | `f1f7b2ef60b4` |
| `docs/status/prohibited-capabilities.md` | Авторитетный текущий документ | `current` | current | нет | `rewritten` | `a37a19f3a1f0` | `537f845c7729` |
| `docs/status/v0_3_18_working_handoff.md` | Текущий справочный документ | `current` | current | нет | `unchanged` | `a9d4629cecd4` | `a9d4629cecd4` |
| `docs/status/version-history.md` | Авторитетный текущий документ | `current` | current | нет | `rewritten` | `b51797ee1565` | `6a9a8559eef4` |
| `docs/third-party-components.md` | Текущий справочный документ | `current` | current | нет | `unchanged` | `c4707c2bfc23` | `c4707c2bfc23` |
| `docs/third-party-notices.md` | Текущий справочный документ | `current` | current | нет | `unchanged` | `337be216ef12` | `337be216ef12` |
| `docs/v0_3_4-design.md` | Текущий справочный документ | `current` | current | нет | `unchanged` | `5b4d4e03a6fb` | `5b4d4e03a6fb` |
| `external_review/README.md` | Текущий справочный документ | `current` | current | нет | `rewritten` | `5d874100335a` | `3b1d3263b434` |
| `incident_reconstruction/CURRENT.md` | Неопределённый документ | `current` | current | нет | `created` | `—` | `64c2f5b80126` |
| `incident_reconstruction/README.md` | Frozen evidence | `frozen` | historical | да | `unchanged` | `615b4e88d018` | `615b4e88d018` |
| `lab/README.md` | Текущий справочный документ | `current` | current | нет | `rewritten` | `cd56b6a33da7` | `4872824e419e` |
| `lab/attack-scenarios.md` | Неопределённый документ | `current` | current | нет | `unchanged` | `a7506488674b` | `a7506488674b` |
| `lab/background/README.md` | Текущий справочный документ | `current` | current | нет | `unchanged` | `df0ab00bb55c` | `df0ab00bb55c` |
| `lab/campaigns/README.md` | Текущий справочный документ | `current` | current | нет | `unchanged` | `9207a2693a09` | `9207a2693a09` |
| `lab/campaigns/v0_3_13/README.md` | Текущий справочный документ | `current` | current | нет | `unchanged` | `7dae5597ddb9` | `7dae5597ddb9` |
| `lab/dataset-methodology.md` | Неопределённый документ | `current` | current | нет | `unchanged` | `cd03d2ea9fc2` | `cd03d2ea9fc2` |
| `lab/docker/README.md` | Текущий справочный документ | `current` | current | нет | `unchanged` | `20ce9b1170ef` | `20ce9b1170ef` |
| `lab/docker/services/control-api/README.md` | Текущий справочный документ | `current` | current | нет | `unchanged` | `4d582a94f886` | `4d582a94f886` |
| `lab/environment/README.md` | Текущий справочный документ | `current` | current | нет | `unchanged` | `78d2defef709` | `78d2defef709` |
| `lab/holdout/README.md` | Текущий справочный документ | `current` | current | нет | `unchanged` | `d54a3f1d126f` | `d54a3f1d126f` |
| `lab/isolation-rules.md` | Неопределённый документ | `current` | current | нет | `unchanged` | `8f52a729527a` | `8f52a729527a` |
| `lab/robustness/README.md` | Текущий справочный документ | `current` | current | нет | `unchanged` | `82d6f933f2c6` | `82d6f933f2c6` |
| `lab/scenario-schedule.md` | Неопределённый документ | `current` | current | нет | `unchanged` | `fe3fb0e4aad8` | `fe3fb0e4aad8` |
| `lab/sensor/README.md` | Текущий справочный документ | `current` | current | нет | `unchanged` | `8cada83e855f` | `8cada83e855f` |
| `lab/training/README.md` | Текущий справочный документ | `current` | current | нет | `unchanged` | `276aee34aca6` | `276aee34aca6` |
| `lab_console/README.md` | Текущий справочный документ | `current` | current | нет | `created` | `—` | `60b7e7bec824` |
| `ml/README.md` | Текущий справочный документ | `current` | current | нет | `rewritten` | `13916b97d5bf` | `5eb74e22fc7a` |
| `ml/analysis/README.md` | Текущий справочный документ | `current` | current | нет | `rewritten` | `eac616994a5a` | `07d5e4db50d1` |
| `ml/audits/v0_3_12_1/README.md` | Текущий справочный документ | `current` | current | нет | `unchanged` | `c21d5f50bc1f` | `c21d5f50bc1f` |
| `ml/decision/README.md` | Текущий справочный документ | `current` | current | нет | `rewritten` | `deb3377f2cc0` | `705e28547016` |
| `ml/experiments/v0_2_4/README.md` | Текущий справочный документ | `current` | current | нет | `unchanged` | `ab6517fe5f1d` | `ab6517fe5f1d` |
| `ml/experiments/v0_3_1/README.md` | Текущий справочный документ | `current` | current | нет | `unchanged` | `50f235aefe0b` | `50f235aefe0b` |
| `ml/experiments/v0_3_10/README.md` | Текущий справочный документ | `current` | current | нет | `unchanged` | `2d3b0a5d897f` | `2d3b0a5d897f` |
| `ml/experiments/v0_3_11/README.md` | Текущий справочный документ | `current` | current | нет | `unchanged` | `4b270f1306e2` | `4b270f1306e2` |
| `ml/experiments/v0_3_12/README.md` | Текущий справочный документ | `current` | current | нет | `unchanged` | `ec8dc32037c8` | `ec8dc32037c8` |
| `ml/experiments/v0_3_12_2/README.md` | Текущий справочный документ | `current` | current | нет | `unchanged` | `24981b1446c0` | `24981b1446c0` |
| `ml/experiments/v0_3_13/README.md` | Текущий справочный документ | `current` | current | нет | `unchanged` | `844cc4bda97b` | `844cc4bda97b` |
| `ml/experiments/v0_3_14/README.md` | Текущий справочный документ | `current` | current | нет | `unchanged` | `e9aa6a9438dc` | `e9aa6a9438dc` |
| `ml/experiments/v0_3_15/README.md` | Текущий справочный документ | `current` | current | нет | `unchanged` | `c1dd33c94a71` | `c1dd33c94a71` |
| `ml/experiments/v0_3_2/README.md` | Текущий справочный документ | `current` | current | нет | `unchanged` | `323bea6a269c` | `323bea6a269c` |
| `ml/experiments/v0_3_3/README.md` | Текущий справочный документ | `current` | current | нет | `unchanged` | `a5c1dbc3837c` | `a5c1dbc3837c` |
| `ml/experiments/v0_3_4/README.md` | Текущий справочный документ | `current` | current | нет | `unchanged` | `176de193ff8c` | `176de193ff8c` |
| `ml/experiments/v0_3_4/provenance_policy.md` | Неопределённый документ | `current` | current | нет | `unchanged` | `ec007c5aa961` | `ec007c5aa961` |
| `ml/experiments/v0_3_5/README.md` | Текущий справочный документ | `current` | current | нет | `unchanged` | `dea71d48b889` | `dea71d48b889` |
| `ml/experiments/v0_3_6/README.md` | Текущий справочный документ | `current` | current | нет | `unchanged` | `43c3cada95c6` | `43c3cada95c6` |
| `ml/experiments/v0_3_7/README.md` | Текущий справочный документ | `current` | current | нет | `unchanged` | `e10d139c5e6f` | `e10d139c5e6f` |
| `ml/experiments/v0_3_8/README.md` | Текущий справочный документ | `current` | current | нет | `unchanged` | `1a3df80ab417` | `1a3df80ab417` |
| `ml/experiments/v0_3_9/README.md` | Текущий справочный документ | `current` | current | нет | `unchanged` | `2a3d6898bb49` | `2a3d6898bb49` |
| `ml/features/README.md` | Текущий справочный документ | `current` | current | нет | `rewritten` | `eb0049b88c27` | `39941b07c9f5` |
| `ml/protocols/index.md` | Генерируемый индекс или представление | `generated` | current | нет | `rewritten` | `6e4d03d3f03e` | `3a7ba294e87a` |
| `ml/reports/index.md` | Генерируемый индекс или представление | `generated` | current | нет | `rewritten` | `446dd4fda977` | `daccac679f5e` |
| `ml/reports/v0_3_15/v0_3_15_summary.md` | Историческое описание | `historical` | historical | нет | `unchanged` | `009a46666439` | `009a46666439` |
| `ml/reports/v0_3_15_1/v0_3_15_1_summary.md` | Frozen evidence | `frozen` | historical | да | `unchanged` | `01d8756742fc` | `01d8756742fc` |
| `ml/reports/v0_3_15_2/v0_3_15_2_summary.md` | Frozen evidence | `frozen` | historical | да | `unchanged` | `0fda64e224c9` | `0fda64e224c9` |
| `ml/reports/v0_3_15_3/auth_failures_root_cause_report.md` | Frozen evidence | `frozen` | historical | да | `unchanged` | `0119310409a2` | `0119310409a2` |
| `ml/reports/v0_3_15_3/v0_3_15_3_summary.md` | Frozen evidence | `frozen` | historical | да | `unchanged` | `a5820696a4e3` | `a5820696a4e3` |
| `ml/reports/v0_3_15_4/v0_3_15_4_summary.md` | Frozen evidence | `frozen` | historical | да | `unchanged` | `824ceda9d7a3` | `824ceda9d7a3` |
| `ml/reports/v0_3_15_5/v0_3_15_5_summary.md` | Frozen evidence | `frozen` | historical | да | `unchanged` | `6c78ab4e24a0` | `6c78ab4e24a0` |
| `ml/reports/v0_3_15_5_1/v0_3_15_5_1_summary.md` | Frozen evidence | `frozen` | historical | да | `unchanged` | `f4755f7b0722` | `f4755f7b0722` |
| `ml/reports/v0_3_16/v0_3_16_summary.md` | Frozen evidence | `frozen` | historical | да | `unchanged` | `1ef0eefbb743` | `1ef0eefbb743` |
| `ml/reports/v0_3_17/v0_3_17_summary.md` | Frozen evidence | `frozen` | historical | да | `unchanged` | `d127a14eae95` | `d127a14eae95` |
| `ml/reports/v0_3_17_1/v0_3_17_1_summary.md` | Frozen evidence | `frozen` | historical | да | `unchanged` | `ce3182f211d2` | `ce3182f211d2` |
| `ml/reports/v0_3_18/v0_3_18_summary.md` | Frozen evidence | `frozen` | historical | да | `unchanged` | `8d3738dd626a` | `8d3738dd626a` |
| `ml/reports/v0_4_0/known_limitations.md` | Frozen evidence | `frozen` | historical | да | `unchanged` | `79991b811226` | `79991b811226` |
| `ml/reports/v0_4_0/reproduction.md` | Frozen evidence | `frozen` | historical | да | `unchanged` | `5e6a706b4230` | `5e6a706b4230` |
| `ml/reports/v0_4_0/v0_4_0_summary.md` | Frozen evidence | `frozen` | historical | да | `unchanged` | `3f21c7ccfbd1` | `3f21c7ccfbd1` |
| `ml/reports/v0_4_1/known_limitations.md` | Frozen evidence | `frozen` | historical | да | `unchanged` | `c9a248936e8f` | `c9a248936e8f` |
| `ml/reports/v0_4_1/reproduction.md` | Frozen evidence | `frozen` | historical | да | `unchanged` | `e583f7187333` | `e583f7187333` |
| `ml/reports/v0_4_1/v0_4_1_summary.md` | Frozen evidence | `frozen` | historical | да | `unchanged` | `d751669bd9c2` | `d751669bd9c2` |
| `ml/reports/v0_4_2/known_limitations.md` | Frozen evidence | `frozen` | historical | да | `unchanged` | `bdb3a434125b` | `bdb3a434125b` |
| `ml/reports/v0_4_2/reproduction.md` | Frozen evidence | `frozen` | historical | да | `unchanged` | `5a08db0fc9bf` | `5a08db0fc9bf` |
| `ml/reports/v0_4_2/v0_4_2_summary.md` | Frozen evidence | `frozen` | historical | да | `unchanged` | `ef2c40f2adf7` | `ef2c40f2adf7` |
| `ml/reports/v0_4_3/known_limitations.md` | Frozen evidence | `frozen` | historical | да | `unchanged` | `9baff454f5e2` | `9baff454f5e2` |
| `ml/reports/v0_4_3/reproduction.md` | Frozen evidence | `frozen` | historical | да | `unchanged` | `58a46ae93c49` | `58a46ae93c49` |
| `ml/reports/v0_4_3/v0_4_3_summary.md` | Frozen evidence | `frozen` | historical | да | `unchanged` | `a73646e83698` | `a73646e83698` |
| `ml/reports/v0_4_3_1/ui_acceptance_report.md` | Историческое описание | `historical` | historical | нет | `unchanged` | `656983fdf033` | `656983fdf033` |
| `ml/reports/v0_4_4/known_limitations.md` | Frozen evidence | `frozen` | historical | да | `unchanged` | `8f72668f34a8` | `8f72668f34a8` |
| `ml/reports/v0_4_4/operator_acceptance_report.md` | Frozen evidence | `frozen` | historical | да | `unchanged` | `70bdc5446226` | `70bdc5446226` |
| `ml/reports/v0_4_4/reproduction.md` | Frozen evidence | `frozen` | historical | да | `unchanged` | `f73277bd0ac9` | `f73277bd0ac9` |
| `ml/reports/v0_4_4/summary.md` | Frozen evidence | `frozen` | historical | да | `unchanged` | `9f948fd6cc9e` | `9f948fd6cc9e` |
| `ml/training/README.md` | Текущий справочный документ | `current` | current | нет | `rewritten` | `9a85d45941ed` | `d460516f6bd3` |
| `rehearsal/README.md` | Текущий справочный документ | `current` | current | нет | `created` | `—` | `a76fb5ae1e1d` |
| `staging/README.md` | Текущий справочный документ | `current` | current | нет | `rewritten` | `42cd64c62b7c` | `d72cdf6547a9` |
| `tools/README.md` | Текущий справочный документ | `current` | current | нет | `rewritten` | `d3eb0f7fec18` | `935fc4e3a13e` |

<!-- generated:end -->

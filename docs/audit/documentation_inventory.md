# Инвентаризация документации

Отчёт фиксирует исходное состояние перед documentation maintenance pass.
Он не изменяет статус проекта и не переоценивает historical evidence.

## Сводка

- Проверено Markdown-документов: `152`.
- Найдено ссылок на отсутствующие локальные targets: `0`.
- Документов с локальными absolute paths: `0`.
- Immutable evidence-документов: `14`.
- Кандидатов на redirect note: `5`.
- Документов с устаревшим current-status контекстом: `7`.

## Правила классификации

- `authoritative=yes` означает текущую точку входа, а не evidence artifact.
- `evidence_immutable=yes` запрещает редакционное изменение содержимого.
- `archive_by_index` и redirect note сохраняют историю без дублирования.
- Absolute paths устраняются только из редактируемой документации; historical
  evidence не переписывается задним числом.

## Документы

| path | category | audience | current_or_historical | authoritative | evidence_immutable | duplicate_of | outdated | broken_links | recommended_action |
|---|---|---|---|---:|---:|---|---:|---:|---|
| `README.md` | root_entry | новый технический читатель | current | yes | no | `—` | yes | 0 | rewrite |
| `backend/README.md` | subsystem_readme | разработчик подсистемы | current | no | no | `—` | no | 0 | keep |
| `collectors/README.md` | subsystem_readme | разработчик подсистемы | current | no | no | `—` | no | 0 | keep |
| `collectors/csv_collector/README.md` | subsystem_readme | разработчик подсистемы | current | no | no | `—` | no | 0 | keep |
| `collectors/suricata_collector/README.md` | subsystem_readme | разработчик подсистемы | current | no | no | `—` | no | 0 | keep |
| `collectors/zeek_collector/README.md` | subsystem_readme | разработчик подсистемы | current | no | no | `—` | no | 0 | keep |
| `datasets/README.md` | subsystem_readme | разработчик подсистемы | current | no | no | `—` | no | 0 | keep |
| `docs/architecture.md` | architecture | разработчик и архитектор | current | no | no | `docs/architecture/overview.md` | yes | 0 | replace_with_redirect_note |
| `docs/architecture/controlled_local_rehearsal_v0_3_17.md` | architecture | разработчик и архитектор | current | no | no | `—` | no | 0 | keep |
| `docs/architecture/index.md` | architecture | разработчик и архитектор | current | no | no | `—` | no | 0 | keep |
| `docs/architecture/staging_connector_v0_3_16.md` | architecture | разработчик и архитектор | current | no | no | `—` | no | 0 | keep |
| `docs/audits/post-v0.3.7-research-integrity-audit.md` | project_documentation | разработчик | historical | no | no | `—` | no | 0 | keep |
| `docs/audits/pre-v0.3.8-runtime-integrity-acceptance.md` | project_documentation | разработчик | historical | no | no | `—` | no | 0 | keep |
| `docs/code-origin-audit.md` | project_documentation | разработчик | current | no | no | `—` | no | 0 | keep |
| `docs/contracts/connector_ingress_ack_v1.md` | project_documentation | разработчик | current | no | no | `—` | no | 0 | keep |
| `docs/contracts/connector_ingress_v1.md` | project_documentation | разработчик | current | no | no | `—` | no | 0 | keep |
| `docs/contracts/index.md` | project_documentation | разработчик | current | no | no | `—` | no | 0 | keep |
| `docs/contracts/operator_projection_v1.md` | project_documentation | разработчик | current | no | no | `—` | no | 0 | keep |
| `docs/contracts/receiver_batch_ack_v1.md` | project_documentation | разработчик | current | no | no | `—` | no | 0 | keep |
| `docs/contracts/rehearsal_observability_v1.md` | project_documentation | разработчик | current | no | no | `—` | no | 0 | keep |
| `docs/contracts/runtime_timing_trace_v2.md` | project_documentation | разработчик | current | no | no | `—` | no | 0 | keep |
| `docs/contracts/shadow-backend-gap-analysis.md` | project_documentation | разработчик | current | no | no | `—` | no | 0 | keep |
| `docs/contracts/shadow-event-v1.md` | project_documentation | разработчик | current | no | no | `—` | no | 0 | keep |
| `docs/contracts/shadow-event-v2.md` | project_documentation | разработчик | current | no | no | `—` | no | 0 | keep |
| `docs/contracts/shadow-trial-runtime.md` | project_documentation | разработчик | current | no | no | `—` | no | 0 | keep |
| `docs/contracts/staging_event_batch_v1.md` | project_documentation | разработчик | current | no | no | `—` | no | 0 | keep |
| `docs/current-capabilities.md` | project_documentation | разработчик | current | no | no | `docs/status/confirmed-capabilities.md` | yes | 0 | replace_with_redirect_note |
| `docs/data-provenance.md` | project_documentation | разработчик | current | no | no | `—` | no | 0 | keep |
| `docs/dependency-licenses.md` | project_documentation | разработчик | current | no | no | `—` | no | 0 | keep |
| `docs/development-history.md` | project_documentation | разработчик | current | no | no | `docs/status/version-history.md` | yes | 0 | replace_with_redirect_note |
| `docs/documentation-policy.md` | project_documentation | разработчик | current | no | no | `—` | no | 0 | keep |
| `docs/experiments.md` | stage_history_or_evidence | аудитор evidence | historical | no | no | `—` | no | 0 | keep |
| `docs/experiments/v0_3_11.md` | stage_history_or_evidence | аудитор evidence | historical | no | no | `—` | no | 0 | keep |
| `docs/experiments/v0_3_12.md` | stage_history_or_evidence | аудитор evidence | historical | no | no | `—` | no | 0 | keep |
| `docs/experiments/v0_3_12_1.md` | stage_history_or_evidence | аудитор evidence | historical | no | no | `—` | no | 0 | keep |
| `docs/experiments/v0_3_12_2.md` | stage_history_or_evidence | аудитор evidence | historical | no | no | `—` | no | 0 | keep |
| `docs/experiments/v0_3_13.md` | stage_history_or_evidence | аудитор evidence | historical | no | no | `—` | no | 0 | keep |
| `docs/experiments/v0_3_14.md` | stage_history_or_evidence | аудитор evidence | historical | no | no | `—` | no | 0 | keep |
| `docs/experiments/v0_3_14_errata.md` | stage_history_or_evidence | аудитор evidence | historical | no | no | `—` | no | 0 | keep |
| `docs/experiments/v0_3_15.md` | stage_history_or_evidence | аудитор evidence | historical | no | no | `—` | no | 0 | keep |
| `docs/experiments/v0_3_15_1.md` | stage_history_or_evidence | аудитор evidence | historical | no | no | `—` | no | 0 | keep |
| `docs/experiments/v0_3_15_2.md` | stage_history_or_evidence | аудитор evidence | historical | no | no | `—` | no | 0 | keep |
| `docs/experiments/v0_3_15_3.md` | stage_history_or_evidence | аудитор evidence | historical | no | no | `—` | no | 0 | keep |
| `docs/experiments/v0_3_15_4.md` | stage_history_or_evidence | аудитор evidence | historical | no | no | `—` | no | 0 | keep |
| `docs/experiments/v0_3_15_4_proposed.md` | stage_history_or_evidence | аудитор evidence | historical | no | no | `—` | no | 0 | keep |
| `docs/experiments/v0_3_15_5.md` | stage_history_or_evidence | аудитор evidence | historical | no | no | `—` | no | 0 | keep |
| `docs/experiments/v0_3_15_5_1.md` | stage_history_or_evidence | аудитор evidence | historical | no | no | `—` | no | 0 | keep |
| `docs/experiments/v0_3_16.md` | stage_history_or_evidence | аудитор evidence | historical | no | no | `—` | no | 0 | keep |
| `docs/experiments/v0_3_17.md` | stage_history_or_evidence | аудитор evidence | historical | no | no | `—` | no | 0 | keep |
| `docs/experiments/v0_3_17_1.md` | stage_history_or_evidence | аудитор evidence | historical | no | no | `—` | no | 0 | keep |
| `docs/experiments/v0_3_18.md` | stage_history_or_evidence | аудитор evidence | historical | no | no | `—` | no | 0 | keep |
| `docs/external_review/README.md` | external_review | внешний reviewer | current | no | no | `—` | no | 0 | keep |
| `docs/external_review/architecture.md` | external_review | внешний reviewer | current | no | no | `—` | no | 0 | keep |
| `docs/external_review/confirmed_scope.md` | external_review | внешний reviewer | current | no | no | `—` | no | 0 | keep |
| `docs/external_review/data_acceptance_policy.md` | external_review | внешний reviewer | current | no | no | `—` | no | 0 | keep |
| `docs/external_review/data_provider_guide.md` | external_review | внешний reviewer | current | no | no | `—` | no | 0 | keep |
| `docs/external_review/data_transfer_requirements.md` | external_review | внешний reviewer | current | no | no | `—` | no | 0 | keep |
| `docs/external_review/evaluator_guide.md` | external_review | внешний reviewer | current | no | no | `—` | no | 0 | keep |
| `docs/external_review/known_limitations.md` | external_review | внешний reviewer | current | no | no | `—` | no | 0 | keep |
| `docs/external_review/label_custodian_guide.md` | external_review | внешний reviewer | current | no | no | `—` | no | 0 | keep |
| `docs/external_review/legal_requirements_checklist.md` | external_review | внешний reviewer | current | no | no | `—` | no | 0 | keep |
| `docs/external_review/metric_policy.md` | external_review | внешний reviewer | current | no | no | `—` | no | 0 | keep |
| `docs/external_review/publication_requirements.md` | external_review | внешний reviewer | current | no | no | `—` | no | 0 | keep |
| `docs/external_review/reproducibility_guide.md` | external_review | внешний reviewer | current | no | no | `—` | no | 0 | keep |
| `docs/external_review/result_approver_guide.md` | external_review | внешний reviewer | current | no | no | `—` | no | 0 | keep |
| `docs/external_review/retention_and_deletion_requirements.md` | external_review | внешний reviewer | current | no | no | `—` | no | 0 | keep |
| `docs/external_review/reviewer_guide.md` | external_review | внешний reviewer | current | no | no | `—` | no | 0 | keep |
| `docs/external_review/stop_conditions.md` | external_review | внешний reviewer | current | no | no | `—` | no | 0 | keep |
| `docs/external_review/trial_operator_guide.md` | external_review | внешний reviewer | current | no | no | `—` | no | 0 | keep |
| `docs/glossary.md` | project_documentation | разработчик | current | no | no | `—` | no | 0 | keep |
| `docs/incident-workflow.md` | project_documentation | разработчик | current | no | no | `—` | no | 0 | keep |
| `docs/index.md` | project_documentation | разработчик | current | yes | no | `—` | no | 0 | rewrite |
| `docs/lab-stand.md` | project_documentation | разработчик | current | no | no | `—` | no | 0 | keep |
| `docs/licensing-audit.md` | project_documentation | разработчик | current | no | no | `—` | no | 0 | keep |
| `docs/limitations.md` | project_documentation | разработчик | current | no | no | `—` | no | 0 | keep |
| `docs/methodology/index.md` | project_documentation | разработчик | current | no | no | `—` | no | 0 | keep |
| `docs/mitre-mapping.md` | project_documentation | разработчик | current | no | no | `—` | no | 0 | keep |
| `docs/modeling.md` | project_documentation | разработчик | current | no | no | `—` | no | 0 | keep |
| `docs/operations/index.md` | project_documentation | разработчик | current | no | no | `—` | no | 0 | keep |
| `docs/operations/local_rehearsal_recovery_runbook.md` | project_documentation | разработчик | current | no | no | `—` | no | 0 | keep |
| `docs/operations/local_rehearsal_runbook.md` | project_documentation | разработчик | current | no | no | `—` | no | 0 | keep |
| `docs/operations/reference_receiver_runbook.md` | project_documentation | разработчик | current | no | no | `—` | no | 0 | keep |
| `docs/performance.md` | project_documentation | разработчик | current | no | no | `—` | no | 0 | keep |
| `docs/post-migration-technical-status.md` | project_documentation | разработчик | current | no | no | `—` | no | 0 | keep |
| `docs/regression-artifact-retention.md` | project_documentation | разработчик | current | no | no | `—` | no | 0 | keep |
| `docs/reports/index.md` | project_documentation | разработчик | current | no | no | `—` | no | 0 | keep |
| `docs/repository-migration.md` | project_documentation | разработчик | current | no | no | `—` | no | 0 | keep |
| `docs/repository-separation-plan.md` | project_documentation | разработчик | current | no | no | `—` | no | 0 | keep |
| `docs/reproducibility.md` | project_documentation | разработчик | current | no | no | `docs/research/reproducibility.md` | yes | 0 | replace_with_redirect_note |
| `docs/roadmap.md` | project_documentation | разработчик | current | no | no | `—` | yes | 0 | rewrite |
| `docs/safety-model.md` | project_documentation | разработчик | current | no | no | `—` | no | 0 | keep |
| `docs/security/index.md` | project_documentation | разработчик | current | no | no | `—` | no | 0 | keep |
| `docs/security/staging_transport_security_v1.md` | project_documentation | разработчик | current | no | no | `—` | no | 0 | keep |
| `docs/sigma-generation.md` | project_documentation | разработчик | current | no | no | `—` | no | 0 | keep |
| `docs/status.md` | status | разработчик и reviewer | current | no | no | `docs/status/current-status.md` | yes | 0 | replace_with_redirect_note |
| `docs/status/v0_3_18_working_handoff.md` | status | разработчик и reviewer | current | no | no | `—` | no | 0 | keep |
| `docs/third-party-components.md` | project_documentation | разработчик | current | no | no | `—` | no | 0 | keep |
| `docs/third-party-notices.md` | project_documentation | разработчик | current | no | no | `—` | no | 0 | keep |
| `docs/v0_3_4-design.md` | project_documentation | разработчик | current | no | no | `—` | no | 0 | keep |
| `lab/README.md` | subsystem_readme | разработчик подсистемы | current | no | no | `—` | no | 0 | keep |
| `lab/attack-scenarios.md` | component_documentation | разработчик | current | no | no | `—` | no | 0 | keep |
| `lab/background/README.md` | subsystem_readme | разработчик подсистемы | current | no | no | `—` | no | 0 | keep |
| `lab/campaigns/README.md` | subsystem_readme | разработчик подсистемы | current | no | no | `—` | no | 0 | keep |
| `lab/campaigns/v0_3_13/README.md` | subsystem_readme | разработчик подсистемы | current | no | no | `—` | no | 0 | keep |
| `lab/dataset-methodology.md` | component_documentation | разработчик | current | no | no | `—` | no | 0 | keep |
| `lab/docker/README.md` | subsystem_readme | разработчик подсистемы | current | no | no | `—` | no | 0 | keep |
| `lab/docker/services/control-api/README.md` | subsystem_readme | разработчик подсистемы | current | no | no | `—` | no | 0 | keep |
| `lab/environment/README.md` | subsystem_readme | разработчик подсистемы | current | no | no | `—` | no | 0 | keep |
| `lab/holdout/README.md` | subsystem_readme | разработчик подсистемы | current | no | no | `—` | no | 0 | keep |
| `lab/isolation-rules.md` | component_documentation | разработчик | current | no | no | `—` | no | 0 | keep |
| `lab/robustness/README.md` | subsystem_readme | разработчик подсистемы | current | no | no | `—` | no | 0 | keep |
| `lab/scenario-schedule.md` | component_documentation | разработчик | current | no | no | `—` | no | 0 | keep |
| `lab/sensor/README.md` | subsystem_readme | разработчик подсистемы | current | no | no | `—` | no | 0 | keep |
| `lab/training/README.md` | subsystem_readme | разработчик подсистемы | current | no | no | `—` | no | 0 | keep |
| `ml/README.md` | subsystem_readme | разработчик подсистемы | current | no | no | `—` | no | 0 | keep |
| `ml/analysis/README.md` | subsystem_readme | разработчик подсистемы | current | no | no | `—` | no | 0 | keep |
| `ml/audits/v0_3_12_1/README.md` | subsystem_readme | разработчик подсистемы | current | no | no | `—` | no | 0 | keep |
| `ml/decision/README.md` | subsystem_readme | разработчик подсистемы | current | no | no | `—` | no | 0 | keep |
| `ml/experiments/v0_2_4/README.md` | subsystem_readme | разработчик подсистемы | current | no | no | `—` | no | 0 | keep |
| `ml/experiments/v0_3_1/README.md` | subsystem_readme | разработчик подсистемы | current | no | no | `—` | no | 0 | keep |
| `ml/experiments/v0_3_10/README.md` | subsystem_readme | разработчик подсистемы | current | no | no | `—` | no | 0 | keep |
| `ml/experiments/v0_3_11/README.md` | subsystem_readme | разработчик подсистемы | current | no | no | `—` | no | 0 | keep |
| `ml/experiments/v0_3_12/README.md` | subsystem_readme | разработчик подсистемы | current | no | no | `—` | no | 0 | keep |
| `ml/experiments/v0_3_12_2/README.md` | subsystem_readme | разработчик подсистемы | current | no | no | `—` | no | 0 | keep |
| `ml/experiments/v0_3_13/README.md` | subsystem_readme | разработчик подсистемы | current | no | no | `—` | no | 0 | keep |
| `ml/experiments/v0_3_14/README.md` | subsystem_readme | разработчик подсистемы | current | no | no | `—` | no | 0 | keep |
| `ml/experiments/v0_3_15/README.md` | subsystem_readme | разработчик подсистемы | current | no | no | `—` | no | 0 | keep |
| `ml/experiments/v0_3_2/README.md` | subsystem_readme | разработчик подсистемы | current | no | no | `—` | no | 0 | keep |
| `ml/experiments/v0_3_3/README.md` | subsystem_readme | разработчик подсистемы | current | no | no | `—` | no | 0 | keep |
| `ml/experiments/v0_3_4/README.md` | subsystem_readme | разработчик подсистемы | current | no | no | `—` | no | 0 | keep |
| `ml/experiments/v0_3_4/provenance_policy.md` | component_documentation | разработчик | current | no | no | `—` | no | 0 | keep |
| `ml/experiments/v0_3_5/README.md` | subsystem_readme | разработчик подсистемы | current | no | no | `—` | no | 0 | keep |
| `ml/experiments/v0_3_6/README.md` | subsystem_readme | разработчик подсистемы | current | no | no | `—` | no | 0 | keep |
| `ml/experiments/v0_3_7/README.md` | subsystem_readme | разработчик подсистемы | current | no | no | `—` | no | 0 | keep |
| `ml/experiments/v0_3_8/README.md` | subsystem_readme | разработчик подсистемы | current | no | no | `—` | no | 0 | keep |
| `ml/experiments/v0_3_9/README.md` | subsystem_readme | разработчик подсистемы | current | no | no | `—` | no | 0 | keep |
| `ml/features/README.md` | subsystem_readme | разработчик подсистемы | current | no | no | `—` | no | 0 | keep |
| `ml/protocols/index.md` | stage_history_or_evidence | аудитор evidence | historical | no | yes | `—` | no | 0 | keep |
| `ml/reports/index.md` | stage_history_or_evidence | аудитор evidence | historical | no | yes | `—` | no | 0 | keep |
| `ml/reports/v0_3_15/v0_3_15_summary.md` | stage_history_or_evidence | аудитор evidence | historical | no | yes | `—` | no | 0 | keep |
| `ml/reports/v0_3_15_1/v0_3_15_1_summary.md` | stage_history_or_evidence | аудитор evidence | historical | no | yes | `—` | no | 0 | keep |
| `ml/reports/v0_3_15_2/v0_3_15_2_summary.md` | stage_history_or_evidence | аудитор evidence | historical | no | yes | `—` | no | 0 | keep |
| `ml/reports/v0_3_15_3/auth_failures_root_cause_report.md` | stage_history_or_evidence | аудитор evidence | historical | no | yes | `—` | no | 0 | keep |
| `ml/reports/v0_3_15_3/v0_3_15_3_summary.md` | stage_history_or_evidence | аудитор evidence | historical | no | yes | `—` | no | 0 | keep |
| `ml/reports/v0_3_15_4/v0_3_15_4_summary.md` | stage_history_or_evidence | аудитор evidence | historical | no | yes | `—` | no | 0 | keep |
| `ml/reports/v0_3_15_5/v0_3_15_5_summary.md` | stage_history_or_evidence | аудитор evidence | historical | no | yes | `—` | no | 0 | keep |
| `ml/reports/v0_3_15_5_1/v0_3_15_5_1_summary.md` | stage_history_or_evidence | аудитор evidence | historical | no | yes | `—` | no | 0 | keep |
| `ml/reports/v0_3_16/v0_3_16_summary.md` | stage_history_or_evidence | аудитор evidence | historical | no | yes | `—` | no | 0 | keep |
| `ml/reports/v0_3_17/v0_3_17_summary.md` | stage_history_or_evidence | аудитор evidence | historical | no | yes | `—` | no | 0 | keep |
| `ml/reports/v0_3_17_1/v0_3_17_1_summary.md` | stage_history_or_evidence | аудитор evidence | historical | no | yes | `—` | no | 0 | keep |
| `ml/reports/v0_3_18/v0_3_18_summary.md` | stage_history_or_evidence | аудитор evidence | historical | no | yes | `—` | no | 0 | keep |
| `ml/training/README.md` | subsystem_readme | разработчик подсистемы | current | no | no | `—` | no | 0 | keep |

## Ограничение

Отчёт анализирует tracked Markdown и локальные относительные ссылки без
сетевой проверки внешних URL. Решение об удалении требует отдельной проверки
входящих ссылок и evidence manifests.

# Филин v0.3.15 — local controlled passive shadow trial

## Назначение

Проверен непрерывный локальный путь от закрытия capture до passive delivery frozen candidate v0.3.11.

## Границы этапа

Trial выполнялся локально; production, backend writes, external network и automatic actions не использовались.

## Frozen candidate

Candidate `v0311:19176acb401be2d4`, artifact `59d2cd75f3f09f5f8976fa2a56417ad10205986f696a3bef5a4fbaba52ff09b7`, manifest `ad8ff7ea42a28847dcf0fc92b76c176d3f0dda0e874bd865dfa4ea3f6fcf888c`.

## v0.3.13 positive control

Результат `True`; prediction `f31bc969f3c014561d15de4861104b0cff3c9b4135eb8e565bb7d84d68e94591`, bundle `5ede6f9365a45766d0d89ef5b25e08f4fd1bfd7c5b47a0e47f300bba5aa750f7`.

## v0.3.14 positive control

Результат `True`; bundle manifest `7939b91e9a2ff8ceb9f763826c8e48b20de54a717062b13b61d669f33ee0d09b`.

## Previous-stage integrity

Официальные результаты v0.3.11–v0.3.14 и backend tree не изменены.

## Protocol freeze

Protocol SHA-256 `69a2527b1a050c5bb92369caf867f0eb964bb817cd0a1eeb8672a63ed9fccb8d`; фактическая capture-window duration 1.0 секунды из `4c2a86e4841bcc57396e7f1cd61a572d2a6dc31ea8a8436c13ee9e8997bbb781`.

## Campaign freeze

Campaign `9cdd55a3058df7d35fb95f6c6826b596db72dc58fa51486c89257c69afa79ce4`; session manifest `2b330794c376c9a70aa0e22d46ef4ca7e7e6a4989c3a519b6b8985ec43500445`; schedules frozen до trial.

## Safety policy

Только internal Docker network; host network, nmap, masscan, реальные credentials и внешние назначения запрещены.

## Trial sessions

Завершено 10/10: shadow_baseline_endurance_001 (18101), shadow_baseline_endurance_002 (18102), shadow_burst_jitter_001 (18201), shadow_burst_jitter_002 (18202), shadow_recovery_overlap_001 (18301), shadow_recovery_overlap_002 (18302), shadow_sink_fault_001 (18401), shadow_sink_fault_002 (18402), shadow_restart_resume_001 (18501), shadow_restart_resume_002 (18502).

## Session groups

baseline_endurance, burst_jitter, recovery_overlap, sink_fault и restart_resume — по две независимые session.

## Seeds

18101, 18102, 18201, 18202, 18301, 18302, 18401, 18402, 18501, 18502

## Episode schedule

80 episodes; schedule SHA-256 `c7cde325605c08cf2bcb0b7c34ddb61007217ac76faac23085bf0009e414789b`.

## Attack-class balance

{"auth_failures": 8, "beacon": 8, "low_rate_dos": 8, "port_scan": 8, "web_probe": 8}

## Benign variants

20 новых variants, каждый встречается дважды в разных половинах и группах.

## Episode-length balance

Длины 2/3/4/5 сбалансированы по session и attack class.

## Continuous background

Окна вне 80 размеченных episodes сохранены как непрерывный benign background.

## Pipeline architecture

Capture close → SHA-256 → Zeek → 51 features → frozen inference → state machine → shadow_event_v1 → exporter → mock sink → checkpoint.

## Capture processing

Canonical captures 1520/1520; missing=0, duplicate=0, fallback=0.

## Zeek processing

Каждый полностью закрытый PCAP обработан контейнеризированным Zeek до перехода к следующему scored window.

## Feature extraction

Создано 1440 online rows; feature table `8611bc4dc32d6e2711d494b5b07c8b66658cfe9bbb577a7b97b30f64ce060745`.

## Frozen feature schema

Ровно 51 feature; schema `cee39edf14f6f68c794eac17379d8855e45370bd849baca9ad2c785435f01fbf`.

## Causal feature audit

Future и label leakage отсутствуют; physical completion order не используется.

## Activity key

Mapping `ff6d07326fa49c66bd73ee0792f5352e52813d0a5d9a5d5132499832d5e48295`; ключи разделены по session и episode/background sequence.

## Causal state persistence

Pending, dedup и alert state разделены по session/activity key и восстанавливаются из atomic checkpoint.

## Checkpoint model

Checkpoint фиксирует capture, Zeek, feature, row, prediction, event hash и sink acknowledgement без labels.

## Blind label vault

Vault `6e6095df21fa7a636d0a57e7fa7c574a35b0782ec0c9a7ae794acc78d107e704` открыт только после 10/10 sessions, 1440 predictions, event freeze и queue drain.

## Blind access audit

Все prediction label/historical/metric/policy read counters равны нулю.

## No-fit audit

fit, partial_fit, calibration fit, conformal fit, threshold/feature/candidate selection counters равны нулю.

## Online inference

Каждое scored window получило inference после закрытия capture и до завершения своей session.

## Unique prediction integrity

1440 unique, duplicate=0, missing=0, after-label-unlock=0; manifest `fe3f31e7f500da8baa6632aae6e1202a83cfdbc22d526d3ed33214aa5ac51ced`.

## Pre-label trial lock

SHA-256 `1690a24ca5ed9b404bd43c348643bff0f7083f5df78b68e54533d526e24acb13`.

## shadow_event_v1

Contract `cc6df6cf93e5dabeafe147ebeb232d04f7a82805e8ddb8409987f44b5cca08fe` использован без изменений.

## Passive exporter

Использованы deterministic identity, canonical JSON, hash chain, bounded spool и at-least-once delivery.

## Local mock sink

Source events=1580, sink unique=1580.

## Source-to-event reconciliation

{"alert_source_without_event_count": 0, "event_without_source_count": 0, "mapped_prediction_row_count": 1440, "prediction_without_observation_count": 0, "review_source_without_event_count": 0, "semantic_duplicate_count": 0, "source_event_reconciliation_passed": true}

## Sink reconciliation

{"event_sets_equal": true, "sink_event_reconciliation_passed": true, "sink_semantic_event_counts": {"alert_continuation": 90, "alert_emitted": 50, "decision_observation": 1440}, "sink_unique_event_count": 1580, "source_semantic_event_counts": {"alert_continuation": 90, "alert_emitted": 50, "decision_observation": 1440}, "source_unique_semantic_event_count": 1580}

## Idempotency

Collisions=0, semantic duplicates=0.

## Hash chain

SHA-256 `218c8c97ebc2fc0730b8d1d49db4705a3edc267b24878a6513a7d38e92a8d8e1`, violations=0.

## Queue

Peak=2, high=0, critical=0.

## Spool

Peak=1595 bytes, recovery passed=True.

## Delivery semantics

at_least_once; exactly-once не заявляется.

## Sink fault sessions

Frozen temporary unavailable, timeout, rate limit, connection reset, slow consumer и ACK faults выполнены без влияния на predictions.

## Restart sessions

Exporter, sink, feature worker и sensor boundaries выполнены по frozen schedule.

## Restart recovery

{"checkpoints_restored": 6, "details": [{"action": "exporter_restart", "checkpoint_restored": true, "hash_chain_preserved": true, "session_id": "shadow_restart_resume_001", "state_restored": true}, {"action": "feature_worker_restart", "checkpoint_restored": true, "hash_chain_preserved": true, "session_id": "shadow_restart_resume_001", "state_restored": true}, {"action": "restart_after_spool_write_before_ack", "checkpoint_restored": true, "hash_chain_preserved": true, "session_id": "shadow_restart_resume_001", "state_restored": true}, {"action": "sensor_process_restart_between_windows", "checkpoint_restored": true, "hash_chain_preserved": true, "session_id": "shadow_restart_resume_002", "state_restored": true}, {"action": "restart_after_ack_before_checkpoint", "checkpoint_restored": true, "hash_chain_preserved": true, "session_id": "shadow_restart_resume_002", "state_restored": true}, {"action": "mock_sink_restart", "checkpoint_restored": true, "hash_chain_preserved": true, "session_id": "shadow_restart_resume_002", "state_restored": true}], "exporter_restarts": 1, "feature_worker_restarts": 1, "first_alert_lost_count": 0, "repeated_inference_count": 0, "restart_recovery_policy_passed": true, "review_event_lost_count": 0, "semantic_duplicate_count": 0, "sensor_restarts": 1, "sink_restarts": 1, "spool_recovery_passed": true, "state_recovery_passed": true, "transport_duplicate_count": 2}

## Transport fault isolation

Transport faults изменяли только retry/spool/delivery latency; model state и thresholds не менялись.

## Fail-safe behavior

Automatic action, network block, backend write, production и external connection counters равны нулю.

## Privacy

Findings=0; raw identifiers, payload, features и labels отсутствуют в events/log/spool.

## Data minimization

Экспорт содержит только минимальное решение и pseudonymous hashes.

## Continuous availability

{"capture_to_feature_success_rate": 1.0, "captured_window_count": 1520, "event_to_sink_eventual_success_rate": 1.0, "exported_source_window_count": 1440, "feature_to_prediction_success_rate": 1.0, "pipeline_window_coverage": 1.0, "predicted_window_count": 1440, "prediction_to_event_success_rate": 1.0, "processed_window_count": 1520, "scheduled_window_count": 1520, "sink_reconciled_window_count": 1440}

## Processing latency

{"alert_end_to_end": {"p50_ms": 777.3963999934494, "p95_ms": 875.8514799876139, "p99_ms": 979.20311999158}, "capture_close_to_sink": {"p50_ms": 774.781800020719, "p95_ms": 906.7794349946779, "p99_ms": 1019.7773389948993}, "capture_close_to_zeek": {"p50_ms": 759.4604999758303, "p95_ms": 883.8704749650788, "p99_ms": 995.4177990183231}, "enqueue_to_sink": {"p50_ms": 0.678999989759177, "p95_ms": 1.0689399903640149, "p99_ms": 1.6049659845884878}, "feature_to_prediction": {"p50_ms": 12.48614999349229, "p95_ms": 16.53412995219696, "p99_ms": 34.41820999723848}, "prediction_to_enqueue": {"p50_ms": 0.8392500458285213, "p95_ms": 1.5216700034216046, "p99_ms": 1.9847670017043124}, "zeek_to_feature": {"p50_ms": 0.9625499951653183, "p95_ms": 1.375030048075132, "p99_ms": 1.9082830008119336}}

## Processing lag

Maximum=1, sustained=0, backlog peak=1.

## Causal-order invariance

8 aggregation profiles equivalent=True; inference не повторялся.

## Window metrics

{"FPR": 0.0, "accuracy": 1.0, "attack_macro_f1": 1.0, "attack_macro_recall": 1.0, "balanced_accuracy": 1.0, "benign_recall": 1.0, "macro_f1": 1.0, "macro_precision": 1.0, "macro_recall": 1.0, "weighted_f1": 1.0}

## Stateful metrics

{"activity_key_collision_count": 0, "continuation_window_count": 90, "cross_activity_contamination_count": 0, "cross_session_contamination_count": 0, "duplicate_false_suppression_count": 0, "duplicate_suppression_count": 90, "duplicate_suppression_precision": 1.0, "eligible_but_not_emitted_count": 0, "first_alert_suppression_count": 0, "pending_window_count": 0, "pre_alert_pending_attack_window_rate": 0.0, "review_window_count": 0, "review_window_rate": 0.0, "state_counts": {"alert_emitted": 50, "benign": 1300, "post_alert_continuation": 90}, "state_machine_extra_delay_count": 0, "unresolved_pending_episode_rate": 0.0}

## Episode metrics

{"alert_window_distribution": {"1": 40}, "attack_episode_count": 40, "attack_episode_recall": 1.0, "benign_episode_count": 40, "benign_episode_false_alert_rate": 0.0, "detection_by_first_window": 1.0, "detection_by_second_window": 1.0, "detection_by_third_window": 1.0, "episode_alert_precision": 1.0, "episode_count": 80, "latency": {"maximum": 1, "mean": 1.0, "median": 1.0}, "unresolved_pending_episode_rate": 0.0}

## Detection latency

{"maximum": 1, "mean": 1.0, "median": 1.0}

## Per-class metrics

Фактический breakdown сохранён в `per_class_metrics.json`.

## Per-session metrics

Фактический breakdown для 10 sessions сохранён в `per_session_metrics.json`.

## Per-group metrics

Фактический breakdown для пяти групп сохранён в `per_group_metrics.json`.

## Per-variant metrics

Все 20 variants сохранены в `per_variant_metrics.json`.

## Per-length metrics

Длины 2/3/4/5 сохранены в `per_length_metrics.json`.

## Calibration

{"frozen_calibration_unchanged": true, "gate": {"Brier": 1.1862892431129854e-07, "ECE": 0.00024557215734122284, "log_loss": 0.00024560902468690013}, "joint": {"Brier": 1.1862892431129854e-07, "ECE": 0.00024557215734122284, "log_loss": 0.00024560902468690013}, "subtype": {"Brier": 1.1862892431129854e-07, "ECE": 0.00024557215734122284, "log_loss": 0.00024560902468690013}}

## Conformal

{"average_set_size": 1.0, "coverage_per_class": {"auth_failures": 1.0, "beacon": 1.0, "benign": 1.0, "low_rate_dos": 1.0, "port_scan": 1.0, "web_probe": 1.0}, "empty_set_rate": 0.0, "frozen_conformal_unchanged": true, "median_set_size": 1.0, "multi_class_rate": 0.0, "overall_coverage": 1.0, "singleton_rate": 1.0, "wrong_only_rate": 0.0}

## Drift

PSI 51 features, JS probability, entropy и conformal set-size рассчитаны post-hoc и не использованы для tuning.

## Failure analysis

{}

## Bootstrap intervals

5000 session-level iterations, seed 42; интервалы сохранены в `bootstrap_intervals.json`.

## Hardware

AMD Ryzen 5 5600X, 64 ГБ RAM, NVIDIA GeForce RTX 5060 Ti, один компьютер.

## Resource profile

Capture 1, Zeek 2, feature 2, prediction 1, exporter 1, metrics 3, bootstrap 6; nested pools отсутствуют.

## CPU and RAM

{"cpu_average_percent": 27.35895833333333, "cpu_median_percent": 24.5, "cpu_p95_percent": 45.1, "effective_thread_count": 12, "gpu_acceleration_used": false, "hardware": {"computers": 1, "cpu": "AMD Ryzen 5 5600X", "gpu": "NVIDIA GeForce RTX 5060 Ti", "ram_gb": 64}, "oversubscription_detected": false, "peak_aggregate_rss_mb": 169.2734375, "swap_growth_mb": 0.0, "unbounded_memory_growth": false, "unbounded_queue_growth": false, "workers": {"bootstrap": 6, "capture": 1, "exporter": 1, "feature": 2, "metrics": 3, "prediction": 1, "zeek": 2}}

## Queue and spool resources

Queue peak=2; spool peak=1595 bytes.

## GPU applicability

gpu_acceleration_used=false.

## Checkpoint and resume

Strict resume passed=True; skipped windows=1440; repeated inference=0.

## Shadow trial bundle

Pre `cfe8d39e3bf60ba062780c950a8c01ce13daa13a685680238e68bbf43d8ee04e`, completion `d6e81621db40bc9f05a37c47aa1f7a9e23c9748050a9b239f376d64aa7826439`, final `fe09945114c3c2fc68e7cb0e9a738c7f6098bbaca7e299b1f5ae4d4b11707124`.

## Bundle validation

Strict validator passed=True.

## Controlled shadow policy

Completed=True, passed=True.

## Readiness for v0.3.16

candidate_ready_for_v0_3_16_staging_connector_readiness=True.

## Prohibited actions

Shadow mode, backend integration, production readiness и automatic enforcement остаются false.

## Limitations

Результат относится только к локальному контролируемому стенду и не доказывает production readiness.

## Next stage

При readiness=true разрешён v0.3.16 staging connector readiness; иначе требуется техническое устранение причин либо новый training cycle при scientific failure.

## Conclusion

Local controlled passive shadow trial завершён с immutable artifacts, post-label metrics и fail-safe transport audit.

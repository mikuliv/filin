# Итоги v0.3.15.2

Проспективное испытание завершено, но имеет отрицательный результат. Новый локальный integrated passive runtime технически доставил все 2490 canonical events без semantic duplicates и unaccounted drops; 35/35 fault-сценариев прошли свои oracle. Однако frozen candidate не выполнил заранее зафиксированные scientific thresholds, а полная ACK privacy surface и точная per-event capture-to-sink latency не были сохранены.

## Научный результат

- benign recall: 1.000000; FPR: 0.000000;
- attack macro recall: 0.800000; attack macro F1: 0.733333;
- attack episode recall: 0.400000; detection by second window: 0.400000;
- auth_failures window recall: 0.000000.

## Решение

`v03152_prospective_runtime_trial_passed=false` и `candidate_ready_for_v0_3_16_staging_connector_readiness=false`. Это не отменяет исторические результаты и не разрешает backend integration, shadow mode, production или automatic enforcement. Следующий допустимый этап — v0.3.15.3 для разбора scientific regression и проектирования нового заранее фиксируемого training/evaluation protocol.

## Технические ограничения

- privacy surfaces: 16 заявленных, raw ACK surface не сохранена;
- performance Profile C throughput: 11.420005 events/s;
- candidate_ready_for_shadow_mode=false, sensor_ready_for_backend_integration=false, production_ready=false.

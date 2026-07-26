# Воспроизведение v0.4.1

```powershell
python tools/incident_reconstruction/run_v041_stage.py
python tools/incident_reconstruction/verify_temporal_bundle.py --bundle ml/reports/v0_4_1/representative_temporal_bundle.json
python -m pytest ml/tests/test_v041_temporal_reconstruction.py -q
python tools/audit/build_v041_manifest.py
python tools/audit/validate_v041_bundle.py
```

Запуск не требует Git, сети, модели или backend для проверки representative bundle.

# Воспроизведение v0.4.0

Из корня репозитория:

```powershell
python -m pytest ml/tests/test_v040_incident_reconstruction.py -q
python tools/incident_reconstruction/run_v040_stage.py --output runtime/v0_4_0_reproduction
python tools/incident_reconstruction/verify_bundle.py --bundle ml/reports/v0_4_0/representative_reconstruction_bundle.json
python tools/audit/validate_v040_bundle.py
```

Построитель не требует Git, сети, модели или backend. Для сравнения смыслового
результата используется canonical JSON и SHA-256 карточки.

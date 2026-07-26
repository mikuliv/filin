# Воспроизведение v0.4.2

```powershell
python tools/incident_reconstruction/run_v042_stage.py
python tools/incident_reconstruction/verify_hypothesis_bundle.py --bundle ml/reports/v0_4_2/representative_hypothesis_bundle.json
python -m pytest ml/tests/test_v042_hypothesis_analysis.py -q
```

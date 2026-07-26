# Воспроизведение v0.4.3

1. `python tools/lab_console/generate_v043_contracts.py`
2. `python tools/lab_console/verify_console.py`
3. `python -m pytest -q -p no:cacheprovider ml/tests/test_v043_lab_console.py`
4. `python tools/lab_console/validate_v043_bundle.py`

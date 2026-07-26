# Запуск лабораторной консоли

Из корня репозитория установите зависимости из `lab_console/requirements.txt`, задайте локальный токен и запустите:

```powershell
$env:FILIN_CONSOLE_TOKEN = "локальный-длинный-случайный-токен"
python -m lab_console --host 127.0.0.1 --port 8043
```

Откройте `http://127.0.0.1:8043` и введите тот же токен. Токен не включается в URL, Git или журналы. Не используйте `0.0.0.0`, reverse proxy и публичный хостинг.

Автономная проверка без браузера:

```powershell
python tools/lab_console/verify_console.py
```

Целевые тесты:

```powershell
python -m pytest -q -p no:cacheprovider ml/tests/test_v043_lab_console.py
```

Локальные БД, logs, cache и exports находятся в `runtime/lab_console` и исключены из Git. Удаление runtime сбрасывает локальные сессии и review-overlay, но не затрагивает frozen evidence bundles.

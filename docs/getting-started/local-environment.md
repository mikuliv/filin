# Локальное окружение

Поддерживаемое окружение разработки использует Python и зависимости,
зафиксированные в `ml/requirements.txt` и `backend/requirements.txt`. Конкретная
локальная буква диска, имя пользователя и расположение runtime не являются
частью tracked configuration.

Минимальная подготовка:

```powershell
python -m pip install -r ml/requirements.txt -r backend/requirements.txt
```

Runtime artifacts, model binaries, PCAP, SQLite, WAL, journals и raw traces
остаются вне Git. Тесты должны использовать project-scoped temporary directory
и sanitized fixtures.

Длительные stage runners нельзя запускать как обычную проверку. Сначала следует
прочитать соответствующий frozen protocol и проверить достаточный объём
локального хранилища.

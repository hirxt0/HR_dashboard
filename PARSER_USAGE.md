### Использование парсера Telegram-каналов

Этот модуль собирает сообщения из публичных Telegram-каналов и превращает их в список `chunks`, который можно сразу класть в таблицу:

```text
CREATE TABLE chunks (
    text     TEXT NOT NULL,  -- основной текст
    metadata TEXT            -- JSON с дополнительными данными
);
```

---


### 1. Основной API модуля `telegram_parser.py`

Из модуля доступны:

- `CHANNEL_URLS` — список Telegram-каналов (можно дополнять/кастомизировать);
- `TelegramMessage` — dataclass сообщения;
- `fetch_all_channels(limit_per_channel: int = 100)` → `List[TelegramMessage]`;
- `GigaChatFilter(api_key: str)` — фильтрация и классификация через GigaChat;
- `messages_as_chunks(messages, filter_instance=None)` → `List[Dict[str, str]]`;
- `messages_as_dicts(messages)` — “сырая” выдача без формата chunks.

---

### 2. Быстрый пример интеграции в наш пайплайн

```python
from telegram_parser import fetch_all_channels, messages_as_chunks, GigaChatFilter


def collect_telegram_chunks(gigachat_api_key: str | None = None, limit_per_channel: int = 50):
    # 1. Сбор сообщений
    messages = fetch_all_channels(limit_per_channel=limit_per_channel)

    # 2. (Опционально) фильтрация через GigaChat
    filter_instance = GigaChatFilter(gigachat_api_key) if gigachat_api_key else None

    # 3. Преобразование в формат для таблицы chunks
    chunks = messages_as_chunks(messages, filter_instance=filter_instance)
    return chunks
```

Дальше `chunks` можно:

- либо сразу писать в БД:

```python
import sqlite3

conn = sqlite3.connect("data.db")
cur = conn.cursor()

for chunk in chunks:
    cur.execute(
        "INSERT INTO chunks (text, metadata) VALUES (?, ?)",
        (chunk["text"], chunk["metadata"]),
    )

conn.commit()
conn.close()
```

- либо передавать дальше в ваш модуль эмбеддингов `GetEmbeddings` (см. `embeddings.py`).

---

### 3. Пример вызова из CLI (для отладки)

В корне проекта:

```bash
# без фильтрации (все сообщения)
python telegram_parser.py
```

С фильтрацией через GigaChat:

```bash
export GIGACHAT_API_KEY="your_api_key_here"      # Linux / macOS
$env:GIGACHAT_API_KEY="your_api_key_here"        # PowerShell / Windows

python telegram_parser.py
```

Скрипт выведет в консоль количество полученных сообщений и список chunks (text + metadata JSON).

---

### 4. Как подключить к существующему коду

1. Убедиться, что файл `telegram_parser.py` лежит в том же модуле/пакете, что и основной код, либо добавить его в `PYTHONPATH`.
2. В нужном модуле:

```python
from telegram_parser import fetch_all_channels, messages_as_chunks, GigaChatFilter
```


### 5. Примерный формат вывода после фильтрации

- Если фильтрация прошла 

```json
{
  "channel": "KarpovCourses",
  "message_id": "KarpovCourses/1234",
  "datetime": "2024-01-01T12:00:00+00:00",
  "permalink": "https://t.me/KarpovCourses/1234",
  "relevance": "RELEVANT",
  "category": "AI_ML_DS",
  "importance": "HIGH",
  "tonality": "POSITIVE",
  "justification": "Новость о запуске новой программы
```

- Минимальный случай, если гига чат не справился

```text
{"channel": "KarpovCourses", "message_id": "KarpovCourses/1234", "datetime": "2024-01-01T12:00:00+00:00", "permalink": "https://t.me/KarpovCourses/1234"}
```


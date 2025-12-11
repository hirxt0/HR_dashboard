import sqlite3
import json

conn = sqlite3.connect("telegram_data.db")
conn.row_factory = sqlite3.Row
c = conn.cursor()

# Очистка старых данных
c.execute("DELETE FROM messages")
c.execute("DELETE FROM metadata")

# Тестовые сообщения
test_messages = [
    {
        "channel": "AI News",
        "message_id": "1",
        "text": "Новый прорыв в машинном обучении от Google",
        "datetime": "2024-01-15",
        "permalink": "https://t.me/ai/1",
        "text_cleaned": "Новый прорыв в машинном обучении от Google",
        "channel_category": "tech"
    },
    {
        "channel": "HR Insights",
        "message_id": "2",
        "text": "Рынок труда в IT показывает рост",
        "datetime": "2024-01-16",
        "permalink": "https://t.me/hr/2",
        "text_cleaned": "Рынок труда в IT показывает рост",
        "channel_category": "hr"
    },
    {
        "channel": "Finance Today",
        "message_id": "3",
        "text": "Банки внедряют AI для анализа рисков",
        "datetime": "2024-01-17",
        "permalink": "https://t.me/finance/3",
        "text_cleaned": "Банки внедряют AI для анализа рисков",
        "channel_category": "finance"
    }
]

# Вставляем сообщения
for msg in test_messages:
    c.execute("""
        INSERT INTO messages(channel, message_id, text, datetime, permalink, text_cleaned, channel_category)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        msg["channel"], msg["message_id"], msg["text"], msg["datetime"],
        msg["permalink"], msg["text_cleaned"], msg["channel_category"]
    ))
    msg_id = c.lastrowid
    
    # Тестовые метаданные
    if "AI" in msg["text"]:
        meta = {
            "tags": ["ИИ", "Machine Learning"],
            "sentiment": "positive",
            "sentiment_score": 0.8,
            "is_insider": True,
            "insider_confidence": 0.9
        }
    elif "HR" in msg["channel"]:
        meta = {
            "tags": ["HR", "Рынок труда"],
            "sentiment": "positive",
            "sentiment_score": 0.6,
            "is_insider": False,
            "insider_confidence": 0.3
        }
    else:
        meta = {
            "tags": ["Банки", "AI", "Финтех"],
            "sentiment": "neutral",
            "sentiment_score": 0.1,
            "is_insider": True,
            "insider_confidence": 0.7
        }
    
    c.execute("""
        INSERT INTO metadata(message_id, tags, sentiment, sentiment_score, is_insider, insider_confidence)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        msg_id,
        json.dumps(meta["tags"]),
        meta["sentiment"],
        meta["sentiment_score"],
        meta["is_insider"],
        meta["insider_confidence"]
    ))

conn.commit()
conn.close()
print("✅ Тестовые данные добавлены!")
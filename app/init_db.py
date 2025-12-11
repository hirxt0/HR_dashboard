#!/usr/bin/env python
"""
Гарантированная инициализация базы данных с данными
"""
import sqlite3
import sys
import os

print("💾 ГАРАНТИРОВАННАЯ ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ")
print("=" * 60)

# Путь к базе данных
DB_PATH = "telegram_data.db"

# Удаляем старую базу (если есть)
if os.path.exists(DB_PATH):
    print(f"🗑️  Удаляю старую базу данных: {DB_PATH}")
    os.remove(DB_PATH)

# Создаем новое подключение
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

print("\n1. Создаю таблицы...")

# Таблица messages
cursor.execute("""
CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel TEXT NOT NULL,
    message_id TEXT,
    text TEXT NOT NULL,
    datetime TEXT,
    permalink TEXT,
    text_cleaned TEXT,
    channel_category TEXT,
    word_count INTEGER DEFAULT 0,
    char_count INTEGER DEFAULT 0,
    has_links BOOLEAN DEFAULT 0,
    has_mentions BOOLEAN DEFAULT 0,
    has_hashtags BOOLEAN DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
)
""")

# Таблица metadata
cursor.execute("""
CREATE TABLE metadata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id INTEGER NOT NULL,
    tags TEXT,
    sentiment TEXT,
    sentiment_score REAL,
    is_insider INTEGER,
    insider_confidence REAL,
    processed_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(message_id) REFERENCES messages(id)
)
""")

print("✅ Таблицы созданы")

# Добавляем тестовые данные
print("\n2. Добавляю тестовые данные...")

test_messages = [
    {
        "channel": "AI_News_RU",
        "message_id": "sample_001",
        "text": "Google представила новую модель Gemini Ultra. Производительность превосходит GPT-4 на 15% в математических задачах.",
        "datetime": "2024-01-20T10:00:00",
        "permalink": "https://t.me/ai_news/1",
        "text_cleaned": "Google представила новую модель Gemini Ultra. Производительность превосходит GPT-4 на 15% в математических задачах.",
        "channel_category": "технологии"
    },
    {
        "channel": "HR_Analytics",
        "message_id": "sample_002",
        "text": "Рынок труда для AI-специалистов: спрос вырос на 40% за год, но зарплаты снизились на 10% из-за увеличения предложения.",
        "datetime": "2024-01-20T11:30:00",
        "permalink": "https://t.me/hr_analytics/2",
        "text_cleaned": "Рынок труда для AI-специалистов: спрос вырос на 40% за год, но зарплаты снизились на 10% из-за увеличения предложения.",
        "channel_category": "hr"
    },
    {
        "channel": "FinTech_Today",
        "message_id": "sample_003",
        "text": "Сбербанк внедряет ИИ для оценки кредитных рисков. Ожидается снижение просрочек на 25% благодаря новой системе.",
        "datetime": "2024-01-20T13:45:00",
        "permalink": "https://t.me/fintech/3",
        "text_cleaned": "Сбербанк внедряет ИИ для оценки кредитных рисков. Ожидается снижение просрочек на 25% благодаря новой системе.",
        "channel_category": "финтех"
    },
    {
        "channel": "Startup_News",
        "message_id": "sample_004",
        "text": "Российский стартап в области компьютерного зрения привлек $10 млн инвестиций. Технология используется для анализа поведения сотрудников.",
        "datetime": "2024-01-20T15:20:00",
        "permalink": "https://t.me/startup/4",
        "text_cleaned": "Российский стартап в области компьютерного зрения привлек $10 млн инвестиций. Технология используется для анализа поведения сотрудников.",
        "channel_category": "бизнес"
    },
    {
        "channel": "Edu_Tech",
        "message_id": "sample_005",
        "text": "МГУ запускает новую магистерскую программу по Data Science для HR-специалистов. Фокус на практическом применении AI в управлении персоналом.",
        "datetime": "2024-01-20T16:50:00",
        "permalink": "https://t.me/edutech/5",
        "text_cleaned": "МГУ запускает новую магистерскую программу по Data Science для HR-специалистов. Фокус на практическом применении AI в управлении персоналом.",
        "channel_category": "образование"
    },
    {
        "channel": "Job_Market",
        "message_id": "sample_006",
        "text": "Аналитики предупреждают о массовых увольнениях в HR-отделах из-за автоматизации процессов. До 30% позиций могут быть сокращены.",
        "datetime": "2024-01-20T18:15:00",
        "permalink": "https://t.me/jobmarket/6",
        "text_cleaned": "Аналитики предупреждают о массовых увольнениях в HR-отделах из-за автоматизации процессов. До 30% позиций могут быть сокращены.",
        "channel_category": "hr"
    },
    {
        "channel": "Data_Science_RU",
        "message_id": "sample_007",
        "text": "Новое исследование показывает: компании, внедрившие AI в HR-процессы, увеличили эффективность найма на 45%.",
        "datetime": "2024-01-20T19:40:00",
        "permalink": "https://t.me/datascience/7",
        "text_cleaned": "Новое исследование показывает: компании, внедрившие AI в HR-процессы, увеличили эффективность найма на 45%.",
        "channel_category": "технологии"
    }
]

for msg in test_messages:
    cursor.execute("""
    INSERT INTO messages (
        channel, message_id, text, datetime, permalink, 
        text_cleaned, channel_category, word_count, char_count
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        msg["channel"],
        msg["message_id"],
        msg["text"],
        msg["datetime"],
        msg["permalink"],
        msg["text_cleaned"],
        msg["channel_category"],
        len(msg["text"].split()),
        len(msg["text"])
    ))

print(f"✅ Добавлено {len(test_messages)} тестовых сообщений")

# Фиксируем изменения
conn.commit()

# Проверяем
print("\n3. Проверяю данные...")
cursor.execute("SELECT COUNT(*) FROM messages")
total = cursor.fetchone()[0]
print(f"Всего сообщений в базе: {total}")

cursor.execute("SELECT channel, COUNT(*) as cnt FROM messages GROUP BY channel")
channels = cursor.fetchall()
print("\n📡 Сообщения по каналам:")
for channel, count in channels:
    print(f"  • {channel}: {count}")

# Закрываем соединение
conn.close()

print("\n" + "=" * 60)
print("🎉 БАЗА ДАННЫХ УСПЕШНО ИНИЦИАЛИЗИРОВАНА!")
print("\nТеперь можно запустить:")
print("1. python run.py -> Выбрать опцию 3 (Обработка AI)")
print("2. python run.py -> Выбрать опцию 4 (Анализ данных)")
print("3. python run.py -> Выбрать опцию 5 (Веб-интерфейс)")
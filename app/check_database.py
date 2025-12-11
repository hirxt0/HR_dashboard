import sqlite3
import json

conn = sqlite3.connect('telegram_data.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("🔍 ПРОВЕРКА БАЗЫ ДАННЫХ")
print("=" * 50)

# 1. Проверяем структуру
print("\n📋 СТРУКТУРА БАЗЫ:")
cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
for table in tables:
    print(f"\nТаблица: {table[0]}")
    print(f"SQL: {table[1][:100]}...")

# 2. Проверяем данные
print("\n" + "=" * 50)
print("📊 ДАННЫЕ В ТАБЛИЦАХ:")

# Таблица messages
cursor.execute("SELECT COUNT(*) as count FROM messages")
msg_count = cursor.fetchone()['count']
print(f"\nmessages: {msg_count} записей")

if msg_count > 0:
    cursor.execute("SELECT id, channel, text FROM messages LIMIT 5")
    messages = cursor.fetchall()
    for msg in messages:
        print(f"  ID:{msg['id']} Канал:{msg['channel']} Текст:{msg['text'][:50]}...")

# Таблица metadata
cursor.execute("SELECT COUNT(*) as count FROM metadata")
meta_count = cursor.fetchone()['count']
print(f"\nmetadata: {meta_count} записей")

if meta_count > 0:
    cursor.execute("SELECT message_id, tags, sentiment FROM metadata LIMIT 5")
    metas = cursor.fetchall()
    for meta in metas:
        print(f"  MessageID:{meta['message_id']} Теги:{meta['tags']} Настроение:{meta['sentiment']}")

# 3. Проверяем необработанные сообщения
print("\n" + "=" * 50)
print("🔍 НЕОБРАБОТАННЫЕ СООБЩЕНИЯ (SQL запрос):")

query = """
SELECT m.id, m.channel, m.text 
FROM messages m
LEFT JOIN metadata md ON m.id = md.message_id
WHERE md.id IS NULL
"""

cursor.execute(query)
unprocessed = cursor.fetchall()
print(f"Найдено: {len(unprocessed)} необработанных сообщений")

for msg in unprocessed[:5]:
    print(f"  ID:{msg['id']} Канал:{msg['channel']}")

# 4. Статистика
print("\n" + "=" * 50)
print("📈 СТАТИСТИКА:")

cursor.execute("SELECT COUNT(DISTINCT channel) as channels FROM messages")
channels = cursor.fetchone()['channels']
print(f"Уникальных каналов: {channels}")

cursor.execute("""
SELECT channel, COUNT(*) as count 
FROM messages 
GROUP BY channel 
ORDER BY count DESC
""")
channel_stats = cursor.fetchall()
if channel_stats:
    print("\nСтатистика по каналам:")
    for stat in channel_stats[:5]:
        print(f"  {stat['channel']}: {stat['count']}")

conn.close()
print("\n✅ Проверка завершена")
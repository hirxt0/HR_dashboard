import sys
sys.path.append('.')
from database import get_db_connection, search_by_tag
import json

conn = get_db_connection()

# 1. Найдем все новости с тегом "дефицит кадров"
cursor = conn.execute('''
SELECT id, text, llm_tags, sentiment 
FROM chunks 
WHERE llm_tags LIKE '%"дефицит кадров"%'
''')

print("🔍 Новости с тегом 'дефицит кадров':")
print("=" * 50)

news_items = cursor.fetchall()
print(f"📊 Всего найдено: {len(news_items)} записей")

sentiment_counts = {'positive': 0, 'negative': 0, 'neutral': 0}

for i, row in enumerate(news_items):
    print(f"\n{i+1}. ID: {row['id']}")
    print(f"   Настроение: {row['sentiment']}")
    print(f"   Текст: {row['text'][:100]}...")
    
    if row['sentiment'] in sentiment_counts:
        sentiment_counts[row['sentiment']] += 1

print(f"\n📈 Распределение настроений:")
total = len(news_items)
for sentiment, count in sentiment_counts.items():
    percentage = (count / total * 100) if total > 0 else 0
    print(f"   {sentiment}: {count} ({percentage:.1f}%)")

# 2. Проверим функцию подсчета тегов
cursor = conn.execute("SELECT llm_tags, sentiment FROM chunks")
all_tags = []
tag_sentiment = {}

for row in cursor.fetchall():
    if not row['llm_tags']:
        continue
        
    try:
        tags = json.loads(row['llm_tags'])
        sentiment = row['sentiment']
        
        for tag in tags:
            if tag not in tag_sentiment:
                tag_sentiment[tag] = {'total': 0, 'positive': 0, 'negative': 0, 'neutral': 0}
            
            tag_sentiment[tag]['total'] += 1
            if sentiment in ['positive', 'negative', 'neutral']:
                tag_sentiment[tag][sentiment] += 1
                
    except Exception as e:
        continue

print(f"\n📊 Статистика по тегу 'дефицит кадров':")
if 'дефицит кадров' in tag_sentiment:
    stats = tag_sentiment['дефицит кадров']
    total = stats['total']
    print(f"   Всего упоминаний: {total}")
    print(f"   Позитивных: {stats['positive']} ({(stats['positive']/total*100) if total > 0 else 0:.1f}%)")
    print(f"   Негативных: {stats['negative']} ({(stats['negative']/total*100) if total > 0 else 0:.1f}%)")
    print(f"   Нейтральных: {stats['neutral']} ({(stats['neutral']/total*100) if total > 0 else 0:.1f}%)")
else:
    print("   ❌ Тег не найден в статистике!")

conn.close()
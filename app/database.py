"""
database.py - Модуль для работы с базой данных
"""
import sqlite3
import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any

DATABASE = 'telegram_data.db'

def get_db_connection():
    """Создание соединения с БД"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    """Инициализация БД если её нет"""
    if not os.path.exists(DATABASE):
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL,
            metadata TEXT,
            llm_tags TEXT,
            sentiment TEXT,
            explanation TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        conn.commit()
        conn.close()
        print(f"Создана новая БД: {DATABASE}")

def create_sample_data():
    """Создание тестовых данных если БД пустая"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM chunks")
    count = cursor.fetchone()[0]
    
    if count == 0:
        base_date = datetime.now()
        dates = [(base_date - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(30)]
        
        sample_data = [
            {
                'text': 'Компания Google объявила о новых инвестициях в искусственный интеллект и машинное обучение. Технологический гигант планирует создать 1000 новых рабочих мест в сфере ИИ в течение следующего года.',
                'metadata': json.dumps({'source': 'tech_news', 'date': dates[0]}),
                'llm_tags': json.dumps(['технологии', 'искусственный интеллект', 'инвестиции', 'работа', 'Google']),
                'sentiment': 'positive',
                'explanation': 'Текст посвящен инвестициям в ИИ и созданию рабочих мест'
            },
            {
                'text': 'Microsoft представляет новую версию Copilot для разработчиков с улучшенной поддержкой Python и JavaScript.',
                'metadata': json.dumps({'source': 'tech_updates', 'date': dates[1]}),
                'llm_tags': json.dumps(['технологии', 'Microsoft', 'разработка', 'инструменты', 'AI']),
                'sentiment': 'positive',
                'explanation': 'Анонс нового инструмента для разработчиков'
            },
            {
                'text': 'Утечка данных в крупной IT-компании: пострадало более 500 тысяч пользователей. Эксперты отмечают рост кибератак на 40% в этом квартале.',
                'metadata': json.dumps({'source': 'security', 'date': dates[2]}),
                'llm_tags': json.dumps(['кибербезопасность', 'данные', 'утечка', 'IT', 'риски']),
                'sentiment': 'negative',
                'explanation': 'Новость о серьезной утечке данных'
            },
            {
                'text': 'Кризис на рынке IT-специалистов продолжает обостряться. Компании сталкиваются с дефицитом квалифицированных кадров, что сказывается на темпах цифровой трансформации.',
                'metadata': json.dumps({'source': 'hr_digest', 'date': dates[3]}),
                'llm_tags': json.dumps(['работа', 'кадры', 'кризис', 'IT', 'дефицит']),
                'sentiment': 'negative',
                'explanation': 'Обсуждается дефицит IT-кадров и его последствия'
            },
            {
                'text': 'Новые исследования показывают, что удаленная работа повышает продуктивность сотрудников на 15%. Компании активно внедряют гибридные форматы работы.',
                'metadata': json.dumps({'source': 'work_trends', 'date': dates[4]}),
                'llm_tags': json.dumps(['работа', 'удаленка', 'продуктивность', 'исследования', 'гибридный формат']),
                'sentiment': 'positive',
                'explanation': 'Текст о преимуществах удаленной работы и исследованиях'
            },
            {
                'text': 'Средняя зарплата разработчиков в России выросла на 20% за год. Наибольший рост отмечается в сферах Data Science и DevOps.',
                'metadata': json.dumps({'source': 'salary_report', 'date': dates[5]}),
                'llm_tags': json.dumps(['зарплата', 'разработчики', 'рынок труда', 'рост', 'Data Science']),
                'sentiment': 'positive',
                'explanation': 'Новость о росте зарплат в IT-сфере'
            },
        ]
        
        for item in sample_data:
            cursor.execute('''
            INSERT INTO chunks (text, metadata, llm_tags, sentiment, explanation)
            VALUES (?, ?, ?, ?, ?)
            ''', (
                item['text'],
                item['metadata'],
                item['llm_tags'],
                item['sentiment'],
                item['explanation']
            ))
        
        conn.commit()
        print(f"Добавлено {len(sample_data)} тестовых записей")
    else:
        print(f"В базе уже есть {count} записей")
    
    conn.close()

def get_all_tags() -> List[str]:
    """Получить все теги из БД"""
    conn = get_db_connection()
    try:
        cursor = conn.execute("SELECT llm_tags FROM chunks WHERE llm_tags IS NOT NULL")
        all_tags = []
        
        for row in cursor.fetchall():
            try:
                tags = json.loads(row['llm_tags'])
                all_tags.extend(tags)
            except:
                pass
        
        return all_tags
    finally:
        conn.close()

def search_by_tag(tag: str, smart_search: bool = False) -> List[Dict[str, Any]]:
    """Поиск новостей по тегу"""
    conn = get_db_connection()
    
    try:
        query = '''
        SELECT id, text, metadata, llm_tags, sentiment, explanation, created_at
        FROM chunks
        WHERE EXISTS (
            SELECT 1 FROM json_each(llm_tags) 
            WHERE LOWER(TRIM(value)) = LOWER(?)
        )
        OR LOWER(text) LIKE ?
        ORDER BY created_at DESC
        LIMIT 50
        '''
        
        search_pattern = f'%{tag.lower()}%'
        cursor = conn.execute(query, (tag.lower(), search_pattern))
        results = cursor.fetchall()
        
        formatted_results = []
        for row in results:
            try:
                llm_tags = json.loads(row['llm_tags']) if row['llm_tags'] else []
                metadata = json.loads(row['metadata']) if row['metadata'] else {}
            except:
                llm_tags = []
                metadata = {}
            
            formatted_results.append({
                'id': row['id'],
                'text': row['text'],
                'llm_tags': llm_tags,
                'sentiment': row['sentiment'],
                'explanation': row['explanation'],
                'metadata': metadata,
                'created_at': row['created_at']
            })
        
        return formatted_results
        
    finally:
        conn.close()

def get_news_paginated(limit: int = 5, offset: int = 0) -> Dict[str, Any]:
    """Получить новости с пагинацией"""
    conn = get_db_connection()
    
    try:
        cursor = conn.execute("SELECT COUNT(*) as total FROM chunks")
        total = cursor.fetchone()['total']
        
        cursor = conn.execute('''
        SELECT id, text, metadata, llm_tags, sentiment, explanation, created_at
        FROM chunks
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
        ''', (limit, offset))
        
        results = cursor.fetchall()
        
        channel_map = {
            'tech_news': 'Технологии',
            'hr_digest': 'HR Дигест',
            'work_trends': 'Тренды работы',
            'startup_news': 'Стартапы',
            'economic_news': 'Экономика',
            'education': 'Образование',
            'security': 'Безопасность',
            'hr_trends': 'HR Тренды',
            'market_analysis': 'Аналитика рынка'
        }
        
        formatted_news = []
        for row in results:
            try:
                llm_tags = json.loads(row['llm_tags']) if row['llm_tags'] else []
                metadata = json.loads(row['metadata']) if row['metadata'] else {}
            except:
                llm_tags = []
                metadata = {}
            
            source = metadata.get('source', 'unknown')
            
            formatted_news.append({
                'id': row['id'],
                'text': row['text'],
                'llm_tags': llm_tags[:5],
                'sentiment': row['sentiment'],
                'channel': channel_map.get(source, 'Другое'),
                'date': metadata.get('date', row['created_at'][:10]),
                'short_text': row['text'][:150] + ('...' if len(row['text']) > 150 else ''),
                'created_at': row['created_at']
            })
        
        return {
            'news': formatted_news,
            'total': total,
            'has_more': offset + limit < total
        }
        
    finally:
        conn.close()
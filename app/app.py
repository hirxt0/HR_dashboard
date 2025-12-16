# app/app.py
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import sqlite3
import json
import os
from datetime import datetime
from collections import Counter

app = Flask(__name__, 
            static_folder='static',
            template_folder='templates')
CORS(app)

# Конфигурация
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
        
        # Создаем таблицу с нужными колонками
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
        sample_data = [
            {
                'text': 'Компания Google объявила о новых инвестициях в искусственный интеллект и машинное обучение. Технологический гигант планирует создать 1000 новых рабочих мест в сфере ИИ в течение следующего года.',
                'metadata': json.dumps({'source': 'tech_news', 'date': '2024-01-15'}),
                'llm_tags': json.dumps(['технологии', 'искусственный интеллект', 'инвестиции', 'работа']),
                'sentiment': 'positive',
                'explanation': 'Текст посвящен инвестициям в ИИ и созданию рабочих мест'
            },
            {
                'text': 'Кризис на рынке IT-специалистов продолжает обостряться. Компании сталкиваются с дефицитом квалифицированных кадров, что сказывается на темпах цифровой трансформации.',
                'metadata': json.dumps({'source': 'hr_digest', 'date': '2024-01-14'}),
                'llm_tags': json.dumps(['работа', 'кадры', 'кризис', 'IT']),
                'sentiment': 'negative',
                'explanation': 'Обсуждается дефицит IT-кадров и его последствия'
            },
            {
                'text': 'Новые исследования показывают, что удаленная работа повышает продуктивность сотрудников на 15%. Компании активно внедряют гибридные форматы работы.',
                'metadata': json.dumps({'source': 'work_trends', 'date': '2024-01-13'}),
                'llm_tags': json.dumps(['работа', 'удаленка', 'продуктивность', 'исследования']),
                'sentiment': 'positive',
                'explanation': 'Текст о преимуществах удаленной работы и исследованиях'
            },
            {
                'text': 'Стартап в области fintech привлек $50 млн инвестиций. Компания разрабатывает инновационные решения для банковского сектора.',
                'metadata': json.dumps({'source': 'startup_news', 'date': '2024-01-12'}),
                'llm_tags': json.dumps(['стартапы', 'финтех', 'инвестиции', 'инновации']),
                'sentiment': 'positive',
                'explanation': 'Новость о привлечении инвестиций fintech-стартапом'
            },
            {
                'text': 'Эксперты прогнозируют рост безработицы в IT-секторе на 5% в следующем квартале. Причина - сокращение бюджетов на digital-проекты.',
                'metadata': json.dumps({'source': 'economic_news', 'date': '2024-01-11'}),
                'llm_tags': json.dumps(['работа', 'IT', 'безработица', 'экономика']),
                'sentiment': 'negative',
                'explanation': 'Прогноз роста безработицы в IT-сфере'
            },
            {
                'text': 'Microsoft запускает новую программу обучения AI-специалистов. Курс будет доступен бесплатно для всех желающих.',
                'metadata': json.dumps({'source': 'education', 'date': '2024-01-10'}),
                'llm_tags': json.dumps(['образование', 'искусственный интеллект', 'обучение', 'технологии']),
                'sentiment': 'positive',
                'explanation': 'Анонс образовательной программы по ИИ от Microsoft'
            },
            {
                'text': 'Проблемы с кибербезопасностью становятся главной угрозой для бизнеса. Утечки данных участились на 30% за последний год.',
                'metadata': json.dumps({'source': 'security', 'date': '2024-01-09'}),
                'llm_tags': json.dumps(['кибербезопасность', 'данные', 'бизнес', 'угрозы']),
                'sentiment': 'negative',
                'explanation': 'Текст о росте угроз кибербезопасности'
            },
            {
                'text': 'Тренд на wellness в корпоративной культуре набирает обороты. Компании инвестируют в здоровье и благополучие сотрудников.',
                'metadata': json.dumps({'source': 'hr_trends', 'date': '2024-01-08'}),
                'llm_tags': json.dumps(['корпоративная культура', 'здоровье', 'тренды', 'бизнес']),
                'sentiment': 'positive',
                'explanation': 'Обзор тренда wellness в компаниях'
            }
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
    
    conn.close()

@app.route('/')
def index():
    """Главная страница"""
    return render_template('index.html')

@app.route('/api/search', methods=['GET'])
def search():
    """Поиск по тегам"""
    tag = request.args.get('tag', '').strip().lower()
    
    if not tag:
        return jsonify({'error': 'Не указан тег для поиска'}), 400
    
    conn = get_db_connection()
    
    try:
        # Поиск по тегам (нечеткий поиск)
        query = '''
        SELECT id, text, metadata, llm_tags, sentiment, explanation,
               created_at
        FROM chunks
        WHERE LOWER(llm_tags) LIKE ? 
           OR LOWER(text) LIKE ?
        ORDER BY created_at DESC
        LIMIT 50
        '''
        
        search_pattern = f'%{tag}%'
        cursor = conn.execute(query, (search_pattern, search_pattern))
        results = cursor.fetchall()
        
        # Преобразуем результаты
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
        
        return jsonify({
            'results': formatted_results,
            'count': len(formatted_results),
            'tag': tag
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Получение статистики"""
    conn = get_db_connection()
    
    try:
        # Общая статистика
        cursor = conn.execute("SELECT COUNT(*) as total FROM chunks")
        total_news = cursor.fetchone()['total']
        
        # Собираем все теги
        cursor.execute("SELECT llm_tags FROM chunks WHERE llm_tags IS NOT NULL")
        all_tags = []
        
        for row in cursor.fetchall():
            try:
                tags = json.loads(row['llm_tags'])
                all_tags.extend(tags)
            except:
                pass
        
        unique_tags = len(set(all_tags))
        
        # Популярные теги (топ-10)
        tag_counter = Counter(all_tags)
        popular_tags = [{'tag': tag, 'count': count} 
                       for tag, count in tag_counter.most_common(10)]
        
        # Активные сигналы (по настроению)
        cursor.execute('''
        SELECT sentiment, COUNT(*) as count
        FROM chunks 
        WHERE sentiment IS NOT NULL
        GROUP BY sentiment
        ''')
        
        sentiments = cursor.fetchall()
        total_signals = sum(row['count'] for row in sentiments)
        
        # Форматируем сигналы для фронтенда
        formatted_signals = []
        signal_id = 1
        
        # Создаем сигналы на основе данных
        signal_types = {
            'negative': {
                'type': 'problem',
                'title': 'Проблемные тренды',
                'icon': 'fas fa-exclamation-triangle',
                'description': 'Негативные тенденции в HR и бизнесе'
            },
            'positive': {
                'type': 'opportunity',
                'title': 'Возможности',
                'icon': 'fas fa-lightbulb',
                'description': 'Позитивные изменения и возможности'
            },
            'neutral': {
                'type': 'early_trend',
                'title': 'Ранние тренды',
                'icon': 'fas fa-chart-line',
                'description': 'Новые зарождающиеся тенденции'
            }
        }
        
        for sentiment_row in sentiments:
            sentiment = sentiment_row['sentiment']
            count = sentiment_row['count']
            
            if sentiment in signal_types:
                signal_info = signal_types[sentiment]
                
                # Создаем несколько сигналов для каждого типа
                for i in range(min(3, count)):  # Максимум 3 сигнала каждого типа
                    formatted_signals.append({
                        'id': signal_id,
                        'title': f"{signal_info['title']} #{i+1}",
                        'description': signal_info['description'],
                        'type': signal_info['type'],
                        'icon': signal_info['icon'],
                        'mentions': count,
                        'trend': 'up' if sentiment == 'positive' else 'down' if sentiment == 'negative' else 'stable'
                    })
                    signal_id += 1
        
        return jsonify({
            'total_news': total_news,
            'unique_tags': unique_tags,
            'total_signals': total_signals,
            'popular_tags': popular_tags,
            'signals': formatted_signals[:6],  # Максимум 6 сигналов
            'update_time': datetime.now().strftime('%d.%m.%Y %H:%M')
        })
        
    except Exception as e:
        print(f"Ошибка получения статистики: {e}")
        return jsonify({
            'total_news': 0,
            'unique_tags': 0,
            'total_signals': 0,
            'popular_tags': [],
            'signals': [],
            'update_time': datetime.now().strftime('%d.%m.%Y %H:%M')
        })
    finally:
        conn.close()

@app.route('/api/news', methods=['GET'])
def get_news():
    """Получение последних новостей"""
    limit = request.args.get('limit', 10, type=int)
    
    conn = get_db_connection()
    
    try:
        cursor = conn.execute('''
        SELECT id, text, metadata, llm_tags, sentiment, explanation,
               created_at
        FROM chunks
        ORDER BY created_at DESC
        LIMIT ?
        ''', (limit,))
        
        results = cursor.fetchall()
        
        formatted_news = []
        for row in results:
            try:
                llm_tags = json.loads(row['llm_tags']) if row['llm_tags'] else []
                metadata = json.loads(row['metadata']) if row['metadata'] else {}
            except:
                llm_tags = []
                metadata = {}
            
            # Определяем источник
            source = metadata.get('source', 'unknown')
            channel_map = {
                'tech_news': 'Технологии',
                'hr_digest': 'HR Дигест',
                'work_trends': 'Тренды работы',
                'startup_news': 'Стартапы',
                'economic_news': 'Экономика',
                'education': 'Образование',
                'security': 'Безопасность',
                'hr_trends': 'HR Тренды'
            }
            
            formatted_news.append({
                'id': row['id'],
                'text': row['text'],
                'llm_tags': llm_tags[:3],  # Берем только 3 тега
                'sentiment': row['sentiment'],
                'channel': channel_map.get(source, 'Другое'),
                'date': metadata.get('date', row['created_at'][:10]),
                'short_text': row['text'][:150] + ('...' if len(row['text']) > 150 else '')
            })
        
        return jsonify({'news': formatted_news})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

if __name__ == '__main__':
    # Инициализируем БД
    init_database()
    create_sample_data()
    
    # Запускаем сервер
    print("=" * 50)
    print("HR Analytics Dashboard запущен!")
    print("Откройте в браузере: http://localhost:5000")
    print("=" * 50)
    
    app.run(debug=True, host='0.0.0.0', port=5000)
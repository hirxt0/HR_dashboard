# app/app.py
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import sqlite3
import json
import os
from datetime import datetime, timedelta
from collections import Counter
import difflib
from typing import List, Tuple, Dict, Any

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
        # Генерируем даты для новостей (последние 30 дней)
        base_date = datetime.now()
        dates = [(base_date - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(30)]
        
        sample_data = [
            # Технологии и ИИ
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
            
            # HR и рынок труда
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
            
            # Стартапы и инвестиции
            {
                'text': 'Стартап в области fintech привлек $50 млн инвестиций. Компания разрабатывает инновационные решения для банковского сектора.',
                'metadata': json.dumps({'source': 'startup_news', 'date': dates[6]}),
                'llm_tags': json.dumps(['стартапы', 'финтех', 'инвестиции', 'инновации', 'банкинг']),
                'sentiment': 'positive',
                'explanation': 'Новость о привлечении инвестиций fintech-стартапом'
            },
            {
                'text': 'Венчурные фонды сокращают инвестиции в ранние стадии на 30%. Эксперты связывают это с общей экономической нестабильностью.',
                'metadata': json.dumps({'source': 'vc_news', 'date': dates[7]}),
                'llm_tags': json.dumps(['инвестиции', 'венчурные фонды', 'экономика', 'сокращение', 'стартапы']),
                'sentiment': 'negative',
                'explanation': 'Новость о сокращении венчурных инвестиций'
            },
            
            # Образование и обучение
            {
                'text': 'Microsoft запускает новую программу обучения AI-специалистов. Курс будет доступен бесплатно для всех желающих.',
                'metadata': json.dumps({'source': 'education', 'date': dates[8]}),
                'llm_tags': json.dumps(['образование', 'искусственный интеллект', 'обучение', 'технологии', 'бесплатно']),
                'sentiment': 'positive',
                'explanation': 'Анонс образовательной программы по ИИ от Microsoft'
            },
            {
                'text': 'Спрос на онлайн-курсы по программированию вырос в 3 раза. Платформы отмечают увеличение пользователей из регионов.',
                'metadata': json.dumps({'source': 'edtech', 'date': dates[9]}),
                'llm_tags': json.dumps(['образование', 'онлайн-курсы', 'программирование', 'тренды', 'edtech']),
                'sentiment': 'positive',
                'explanation': 'Новость о росте спроса на онлайн-образование'
            },
            
            # Экономика и бизнес
            {
                'text': 'Эксперты прогнозируют рост безработицы в IT-секторе на 5% в следующем квартале. Причина - сокращение бюджетов на digital-проекты.',
                'metadata': json.dumps({'source': 'economic_news', 'date': dates[10]}),
                'llm_tags': json.dumps(['работа', 'IT', 'безработица', 'экономика', 'сокращения']),
                'sentiment': 'negative',
                'explanation': 'Прогноз роста безработицы в IT-сфере'
            },
            {
                'text': 'Корпорации внедряют 4-дневную рабочую неделю. Первые результаты показывают рост удовлетворенности сотрудников.',
                'metadata': json.dumps({'source': 'business_innovation', 'date': dates[11]}),
                'llm_tags': json.dumps(['работа', 'инновации', 'корпоративная культура', 'продуктивность', 'эксперименты']),
                'sentiment': 'positive',
                'explanation': 'Новость о внедрении 4-дневной рабочей недели'
            },
            
            # Кибербезопасность
            {
                'text': 'Проблемы с кибербезопасностью становятся главной угрозой для бизнеса. Утечки данных участились на 30% за последний год.',
                'metadata': json.dumps({'source': 'security', 'date': dates[12]}),
                'llm_tags': json.dumps(['кибербезопасность', 'данные', 'бизнес', 'угрозы', 'риски']),
                'sentiment': 'negative',
                'explanation': 'Текст о росте угроз кибербезопасности'
            },
            {
                'text': 'Новые стандарты шифрования данных приняты на международном уровне. Компании должны обновить системы до конца года.',
                'metadata': json.dumps({'source': 'security_standards', 'date': dates[13]}),
                'llm_tags': json.dumps(['кибербезопасность', 'стандарты', 'шифрование', 'регулирование', 'комплаенс']),
                'sentiment': 'neutral',
                'explanation': 'Информация о новых стандартах безопасности'
            },
            
            # Корпоративная культура
            {
                'text': 'Тренд на wellness в корпоративной культуре набирает обороты. Компании инвестируют в здоровье и благополучие сотрудников.',
                'metadata': json.dumps({'source': 'hr_trends', 'date': dates[14]}),
                'llm_tags': json.dumps(['корпоративная культура', 'здоровье', 'тренды', 'бизнес', 'wellness']),
                'sentiment': 'positive',
                'explanation': 'Обзор тренда wellness в компаниях'
            },
            {
                'text': 'Конфликты в удаленных командах участились на 25%. Психологи рекомендуют внедрять регулярные check-in встречи.',
                'metadata': json.dumps({'source': 'hr_research', 'date': dates[15]}),
                'llm_tags': json.dumps(['удаленка', 'конфликты', 'команды', 'психология', 'менеджмент']),
                'sentiment': 'negative',
                'explanation': 'Исследование о конфликтах в удаленных командах'
            },
            
            # Нейтральные и аналитические новости
            {
                'text': 'Согласно отчету аналитиков, рынок гибридной работы продолжает развиваться стабильными темпами. Большинство компаний сохраняют текущие форматы работы без значительных изменений.',
                'metadata': json.dumps({'source': 'market_analysis', 'date': dates[16]}),
                'llm_tags': json.dumps(['работа', 'гибридный формат', 'аналитика', 'тренды', 'стабильность']),
                'sentiment': 'neutral',
                'explanation': 'Обзор текущего состояния рынка гибридной работы'
            },
            {
                'text': 'Исследование: 60% компаний планируют увеличить бюджет на цифровую трансформацию в следующем году. Основные инвестиции направлены в автоматизацию процессов.',
                'metadata': json.dumps({'source': 'digital_transformation', 'date': dates[17]}),
                'llm_tags': json.dumps(['цифровая трансформация', 'инвестиции', 'автоматизация', 'бюджет', 'исследование']),
                'sentiment': 'neutral',
                'explanation': 'Аналитика бюджетов на цифровую трансформацию'
            },
            
            # Новые технологии
            {
                'text': 'Квантовые компьютеры становятся коммерчески доступными. Первые промышленные применения ожидаются в фармацевтике и логистике.',
                'metadata': json.dumps({'source': 'emerging_tech', 'date': dates[18]}),
                'llm_tags': json.dumps(['квантовые вычисления', 'технологии', 'инновации', 'фармацевтика', 'логистика']),
                'sentiment': 'positive',
                'explanation': 'Новость о коммерциализации квантовых компьютеров'
            },
            {
                'text': 'Эксперты предупреждают о рисках нерегулируемого использования генеративного ИИ. Возможны нарушения авторских прав и этические проблемы.',
                'metadata': json.dumps({'source': 'ai_ethics', 'date': dates[19]}),
                'llm_tags': json.dumps(['искусственный интеллект', 'этика', 'регулирование', 'риски', 'генеративный AI']),
                'sentiment': 'negative',
                'explanation': 'Обсуждение этических проблем генеративного ИИ'
            },
            
            # Дополнительные разнообразные новости
            {
                'text': 'Рынок EdTech показывает рекордный рост: объем инвестиций превысил $1 млрд. Российские стартапы привлекают внимание международных фондов.',
                'metadata': json.dumps({'source': 'investment_news', 'date': dates[20]}),
                'llm_tags': json.dumps(['EdTech', 'инвестиции', 'стартапы', 'образование', 'рекорд']),
                'sentiment': 'positive',
                'explanation': 'Новость о росте инвестиций в образовательные технологии'
            },
            {
                'text': 'Сокращение штата в крупной IT-компании: уволено 10% сотрудников. Руководство объясняет это реструктуризацией бизнеса.',
                'metadata': json.dumps({'source': 'corporate_news', 'date': dates[21]}),
                'llm_tags': json.dumps(['сокращения', 'IT', 'реструктуризация', 'компания', 'увольнения']),
                'sentiment': 'negative',
                'explanation': 'Новость о массовых увольнениях в IT-компании'
            },
            {
                'text': 'Новое исследование: разнообразие в командах повышает инновационность на 35%. Компании внедряют программы инклюзивности.',
                'metadata': json.dumps({'source': 'diversity_research', 'date': dates[22]}),
                'llm_tags': json.dumps(['разнообразие', 'инновации', 'команды', 'исследование', 'инклюзивность']),
                'sentiment': 'positive',
                'explanation': 'Исследование о влиянии разнообразия на инновации'
            },
            {
                'text': 'Переход на отечественное ПО: компании сталкиваются с техническими сложностями. Сроки миграции могут быть перенесены.',
                'metadata': json.dumps({'source': 'tech_migration', 'date': dates[23]}),
                'llm_tags': json.dumps(['миграция', 'ПО', 'технологии', 'сложности', 'отечественное']),
                'sentiment': 'negative',
                'explanation': 'Новость о проблемах при переходе на отечественное ПО'
            },
            {
                'text': 'Блокчейн-технологии находят применение в HR: проверка дипломов и трудовая история. Пилотные проекты запущены в крупных корпорациях.',
                'metadata': json.dumps({'source': 'blockchain_hr', 'date': dates[24]}),
                'llm_tags': json.dumps(['блокчейн', 'HR', 'технологии', 'инновации', 'верификация']),
                'sentiment': 'positive',
                'explanation': 'Применение блокчейна в HR-процессах'
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
        print(f"Уникальных дат: {len(dates)}")
        print(f"Примеры тегов: технологии, ИИ, работа, кибербезопасность, инвестиции, стартапы, образование, зарплата, удаленка")
        
    else:
        # Проверим существующие данные
        print(f"В базе уже есть {count} записей")
        
        # Посчитаем уникальные теги
        cursor.execute("SELECT llm_tags FROM chunks WHERE llm_tags IS NOT NULL")
        all_tags = []
        
        for row in cursor.fetchall():
            try:
                tags = json.loads(row['llm_tags'])
                all_tags.extend(tags)
            except:
                pass
        
        unique_tags = len(set(all_tags))
        print(f"Уникальных тегов в базе: {unique_tags}")
        print("Примеры тегов:", list(set(all_tags))[:10])
    
    conn.close()

def normalize_text(text: str) -> str:
    """Нормализация текста для сравнения"""
    if not text:
        return ""
    
    # Приводим к нижнему регистру
    text = text.lower()
    
    # Заменяем ё на е
    text = text.replace('ё', 'е')
    
    # Удаляем лишние символы, оставляем только буквы и цифры
    text = ''.join(c for c in text if c.isalnum() or c.isspace())
    
    # Удаляем множественные пробелы
    text = ' '.join(text.split())
    
    return text

def calculate_similarity(text1: str, text2: str) -> float:
    """Вычисление схожести двух строк"""
    if not text1 or not text2:
        return 0.0
    
    # Нормализуем строки
    norm1 = normalize_text(text1)
    norm2 = normalize_text(text2)
    
    # Если одна строка является подстрокой другой
    if norm1 in norm2 or norm2 in norm1:
        return 0.9
    
    # Используем SequenceMatcher для вычисления схожести
    return difflib.SequenceMatcher(None, norm1, norm2).ratio()

class TagSuggester:
    """Класс для предложения тегов"""
    
    def __init__(self):
        self.all_tags = []
        self.tag_counts = {}
        self._initialized = False
    
    def initialize(self):
        """Инициализация списка тегов"""
        if self._initialized:
            return
        
        conn = get_db_connection()
        try:
            cursor = conn.execute("SELECT llm_tags FROM chunks WHERE llm_tags IS NOT NULL")
            
            # Собираем все теги и их частоту
            for row in cursor.fetchall():
                try:
                    tags = json.loads(row['llm_tags'])
                    for tag in tags:
                        self.all_tags.append(tag)
                        self.tag_counts[tag] = self.tag_counts.get(tag, 0) + 1
                except:
                    pass
            
            # Убираем дубликаты и сортируем по частоте
            unique_tags = list(set(self.all_tags))
            self.all_tags = sorted(unique_tags, key=lambda x: self.tag_counts.get(x, 0), reverse=True)
            
            self._initialized = True
            print(f"Загружено {len(self.all_tags)} уникальных тегов")
            
        except Exception as e:
            print(f"Ошибка инициализации TagSuggester: {e}")
        finally:
            conn.close()
    
    def get_suggestions(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Получение предложений для запроса"""
        if not query or len(query) < 2:
            return []

        if not self._initialized:
            self.initialize()

        query_normalized = normalize_text(query)
        suggestions = []

        for tag in self.all_tags:
            # Пропускаем слишком короткие теги
            if len(tag) < 3:
                continue
            
            # Вычисляем схожесть
            similarity = calculate_similarity(query, tag)
            is_exact = normalize_text(tag) == query_normalized

            # Проверяем, содержит ли тег запрос или запрос содержит тег
            contains_query = query_normalized in normalize_text(tag)
            query_contains_tag = normalize_text(tag) in query_normalized

            # Используем реальную схожесть без искусственного увеличения
            # Но устанавливаем более высокий приоритет для частичных совпадений

            # Устанавливаем пороги схожести
            if is_exact:
                # Точное совпадение - самый высокий приоритет
                min_similarity = 0.0  # Принимаем всегда
                # Для точного совпадения устанавливаем similarity = 1.0
                similarity = 1.0
            elif contains_query or query_contains_tag:
                # Частичное совпадение - средний приоритет
                min_similarity = 0.3
                # Для частичных совпадений немного повышаем схожесть
                # но не слишком сильно, чтобы проценты были реалистичными
                similarity = min(0.9, similarity * 1.2)  # Увеличиваем на 20%, но не более 90%
            else:
                # Просто похожие теги - самый низкий приоритет
                min_similarity = 0.6

            # Добавляем тег в предложения если превышен порог
            if similarity >= min_similarity:
                suggestions.append({
                    'tag': tag,
                    'similarity': similarity,
                    'is_exact': is_exact,
                    'count': self.tag_counts.get(tag, 0)
                })

        # Сортируем по приоритету: точные совпадения -> схожесть -> частота использования
        suggestions.sort(key=lambda x: (
            -x['is_exact'],  # Точные совпадения вначале
            -x['similarity'],  # Затем по схожести
            -x['count']  # Затем по частоте
        ))

        # Возвращаем только уникальные теги
        seen_tags = set()
        unique_suggestions = []

        for suggestion in suggestions:
            if suggestion['tag'] not in seen_tags:
                seen_tags.add(suggestion['tag'])
                unique_suggestions.append(suggestion)

                if len(unique_suggestions) >= limit:
                    break
                
        return unique_suggestions

# Инициализируем TagSuggester
tag_suggester = TagSuggester()

def find_best_match(input_tag: str, available_tags: List[str], threshold: float = 0.6) -> Tuple[str, bool]:
    """Поиск наилучшего совпадения с исправлением опечаток"""
    if not input_tag or not available_tags:
        return input_tag, False
    
    input_normalized = normalize_text(input_tag)
    
    # Сначала ищем точные совпадения
    for tag in available_tags:
        if normalize_text(tag) == input_normalized:
            return tag, False
    
    # Ищем похожие теги
    best_match = None
    best_ratio = 0
    
    for tag in available_tags:
        ratio = calculate_similarity(input_tag, tag)
        if ratio > best_ratio and ratio >= threshold:
            best_ratio = ratio
            best_match = tag
    
    if best_match:
        return best_match, True
    
    return input_tag, False

@app.route('/')
def index():
    """Главная страница"""
    return render_template('index.html')

@app.route('/api/search', methods=['GET'])
def search():
    """Поиск по тегам с исправлением опечаток"""
    tag = request.args.get('tag', '').strip()
    smart_search = request.args.get('smart', 'false').lower() == 'true'
    
    if not tag:
        return jsonify({'error': 'Не указан тег для поиска'}), 400
    
    conn = get_db_connection()
    
    try:
        # Получаем все доступные теги для исправления опечаток
        cursor = conn.execute("SELECT DISTINCT llm_tags FROM chunks WHERE llm_tags IS NOT NULL")
        all_tags = []
        for row in cursor.fetchall():
            try:
                tags = json.loads(row['llm_tags'])
                all_tags.extend(tags)
            except:
                pass
        
        unique_tags = list(set(all_tags))
        corrected_tag = tag
        was_corrected = False
        
        # Исправляем опечатки если включен smart-поиск
        if smart_search and unique_tags:
            corrected_tag, was_corrected = find_best_match(tag, unique_tags)
        
        # Поиск по тегам (регистронезависимый)
        query = '''
        SELECT id, text, metadata, llm_tags, sentiment, explanation,
               created_at
        FROM chunks
        WHERE EXISTS (
            SELECT 1 FROM json_each(llm_tags) 
            WHERE LOWER(TRIM(value)) = LOWER(?)
        )
        OR LOWER(text) LIKE ?
        ORDER BY created_at DESC
        LIMIT 50
        '''
        
        search_pattern = f'%{corrected_tag.lower()}%'
        cursor = conn.execute(query, (corrected_tag.lower(), search_pattern))
        results = cursor.fetchall()
        
        # Если не нашли с исправленным тегом, ищем с исходным
        if len(results) == 0 and was_corrected:
            cursor = conn.execute(query, (tag.lower(), f'%{tag.lower()}%'))
            results = cursor.fetchall()
            corrected_tag = tag
            was_corrected = False
        
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
            'tag': tag,
            'corrected_tag': corrected_tag if was_corrected else None,
            'was_corrected': was_corrected
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
        
        # Собираем все теги - БОЛЕЕ НАДЕЖНЫЙ ВАРИАНТ
        cursor.execute("SELECT llm_tags FROM chunks WHERE llm_tags IS NOT NULL AND llm_tags != ''")
        all_tags = []
        tag_errors = 0
        
        print(f"Всего записей с тегами: {cursor.rowcount}")
        
        for row in cursor.fetchall():
            tags_json = row['llm_tags']
            if not tags_json or tags_json.strip() == '':
                continue
                
            try:
                tags = json.loads(tags_json)
                if isinstance(tags, list):
                    all_tags.extend(tags)
                else:
                    print(f"Ошибка: теги не список: {tags_json}")
                    tag_errors += 1
            except json.JSONDecodeError as e:
                print(f"Ошибка парсинга JSON: {e}, данные: {tags_json}")
                tag_errors += 1
            except Exception as e:
                print(f"Другая ошибка: {e}")
                tag_errors += 1
        
        # ОТЛАДОЧНАЯ ИНФОРМАЦИЯ
        print(f"Собрано тегов: {len(all_tags)}")
        print(f"Ошибок парсинга: {tag_errors}")
        
        unique_tags = len(set(all_tags))
        
        # Популярные теги (топ-15 для лучшего исправления)
        from collections import Counter
        tag_counter = Counter(all_tags)
        popular_tags = [{'tag': tag, 'count': count} 
                       for tag, count in tag_counter.most_common(15)]
        
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
            'update_time': datetime.now().strftime('%d.%m.%Y %H:%M'),
            'debug_info': {  # Добавляем отладочную информацию
                'total_tags_collected': len(all_tags),
                'tag_parsing_errors': tag_errors,
                'tag_samples': list(set(all_tags))[:10] if all_tags else []
            }
        })
        
    except Exception as e:
        print(f"Ошибка получения статистики: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'total_news': 0,
            'unique_tags': 0,
            'total_signals': 0,
            'popular_tags': [],
            'signals': [],
            'update_time': datetime.now().strftime('%d.%m.%Y %H:%M'),
            'error': str(e)
        })
    finally:
        conn.close()

@app.route('/api/news', methods=['GET'])
def get_news():
    """Получение последних новостей с пагинацией"""
    limit = request.args.get('limit', 5, type=int)
    offset = request.args.get('offset', 0, type=int)
    
    conn = get_db_connection()
    
    try:
        # Сначала получаем общее количество новостей
        cursor = conn.execute("SELECT COUNT(*) as total FROM chunks")
        total = cursor.fetchone()['total']
        
        # Затем получаем новости для текущей страницы
        cursor = conn.execute('''
        SELECT id, text, metadata, llm_tags, sentiment, explanation,
               created_at
        FROM chunks
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
        ''', (limit, offset))
        
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
                'hr_trends': 'HR Тренды',
                'market_analysis': 'Аналитика рынка'
            }
            
            formatted_news.append({
                'id': row['id'],
                'text': row['text'],
                'llm_tags': llm_tags[:5],  # Берем только 5 тегов
                'sentiment': row['sentiment'],
                'channel': channel_map.get(source, 'Другое'),
                'date': metadata.get('date', row['created_at'][:10]),
                'short_text': row['text'][:150] + ('...' if len(row['text']) > 150 else ''),
                'created_at': row['created_at']
            })
        
        return jsonify({
            'news': formatted_news,
            'total': total,
            'limit': limit,
            'offset': offset,
            'has_more': offset + limit < total
        })
        
    except Exception as e:
        print(f"Ошибка получения новостей: {e}")
        return jsonify({
            'news': [],
            'total': 0,
            'error': str(e)
        }), 500
    finally:
        conn.close()

@app.route('/api/tags/suggest', methods=['GET'])
def suggest_tags():
    """Предложение тегов по частичному совпадению"""
    query = request.args.get('q', '').strip()
    
    if not query or len(query) < 2:
        return jsonify({'suggestions': []})
    
    try:
        # Получаем предложения от TagSuggester
        suggestions = tag_suggester.get_suggestions(query, limit=5)
        
        # Фильтруем слишком странные предложения (низкая схожесть)
        filtered_suggestions = [
            s for s in suggestions 
            if s['is_exact'] or s['similarity'] >= 0.4
        ]
        
        return jsonify({
            'suggestions': filtered_suggestions[:5],  # Максимум 5 предложений
            'query': query
        })
        
    except Exception as e:
        print(f"Ошибка получения предложений: {e}")
        return jsonify({'suggestions': []})

@app.route('/api/tags/count', methods=['GET'])
def get_tags_count():
    """Получение количества тегов"""
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
        
        unique_tags = len(set(all_tags))
        
        return jsonify({
            'total_tags': len(all_tags),
            'unique_tags': unique_tags,
            'tags_list': list(set(all_tags))[:50]  # Топ 50 тегов
        })
        
    except Exception as e:
        print(f"Ошибка получения количества тегов: {e}")
        return jsonify({
            'total_tags': 0,
            'unique_tags': 0,
            'tags_list': []
        })
    finally:
        conn.close()

if __name__ == '__main__':
    # Инициализируем БД
    init_database()
    create_sample_data()
    
    # Инициализируем TagSuggester
    tag_suggester.initialize()
    
    # Запускаем сервер
    print("=" * 50)
    print("HR Analytics Dashboard запущен!")
    print("Откройте в браузере: http://localhost:5000")
    print("=" * 50)
    print("Добавлена нейтральная новость для тестирования")
    print("Теперь в базе есть позитивные, негативные и нейтральные записи")
    print("Всего записей: 9")
    print("Теги: технологии, искусственный интеллект, инвестиции, работа, кадры, кризис, IT, удаленка, продуктивность, исследования, стартапы, финтех, инновации, безработица, экономика, образование, обучение, кибербезопасность, данные, бизнес, угрозы, корпоративная культура, здоровье, тренды, гибридный формат, аналитика, стабильность")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
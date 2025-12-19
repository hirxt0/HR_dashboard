"""
app.py - Главный файл Flask приложения
"""
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS

# Импортируем модули
from database import (
    init_database, 
    create_sample_data, 
    search_by_tag,
    get_news_paginated,
    get_all_tags
)
from datetime import datetime

from tag_suggester import TagSuggester, find_best_match
from stats import (
    get_dashboard_stats,
    get_sentiment_distribution,
    get_top_tags,
    get_tags_info
)

app = Flask(__name__, 
            static_folder='static',
            template_folder='templates')
CORS(app)

# Инициализируем TagSuggester
tag_suggester = TagSuggester()

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
    
    try:
        # Получаем все доступные теги для исправления опечаток
        all_tags = get_all_tags()
        unique_tags = list(set(all_tags))
        
        corrected_tag = tag
        was_corrected = False
        
        # Исправляем опечатки если включен smart-поиск
        if smart_search and unique_tags:
            corrected_tag, was_corrected = find_best_match(tag, unique_tags)
        
        # Поиск по тегам
        results = search_by_tag(corrected_tag)
        
        # Если не нашли с исправленным тегом, ищем с исходным
        if len(results) == 0 and was_corrected:
            results = search_by_tag(tag)
            corrected_tag = tag
            was_corrected = False
        
        return jsonify({
            'results': results,
            'count': len(results),
            'tag': tag,
            'corrected_tag': corrected_tag if was_corrected else None,
            'was_corrected': was_corrected
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Получение статистики"""
    try:
        stats = get_dashboard_stats()
        
        # Добавляем отладочную информацию
        if 'signals' in stats:
            print(f"📊 Получено сигналов: {len(stats['signals'])}")
            for i, signal in enumerate(stats['signals']):
                print(f"  Сигнал {i+1}: {signal.get('title', 'Без названия')}")
                print(f"    Тег: {signal.get('tag', 'нет')}")
                print(f"    Тип: {signal.get('type', 'нет')}")
        
        return jsonify(stats)
    except Exception as e:
        print(f"❌ Ошибка в /api/stats: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/news', methods=['GET'])
def get_news():
    """Получение последних новостей с пагинацией"""
    limit = request.args.get('limit', 5, type=int)
    offset = request.args.get('offset', 0, type=int)
    
    try:
        result = get_news_paginated(limit, offset)
        return jsonify({
            'news': result['news'],
            'total': result['total'],
            'limit': limit,
            'offset': offset,
            'has_more': result['has_more']
        })
    except Exception as e:
        print(f"Ошибка получения новостей: {e}")
        return jsonify({
            'news': [],
            'total': 0,
            'error': str(e)
        }), 500

@app.route('/api/tags/suggest', methods=['GET'])
def suggest_tags():
    """Предложение тегов по частичному совпадению"""
    query = request.args.get('q', '').strip()
    
    if not query or len(query) < 2:
        return jsonify({'suggestions': []})
    
    try:
        suggestions = tag_suggester.get_suggestions(query, limit=5)
        
        # Фильтруем слишком странные предложения
        filtered_suggestions = [
            s for s in suggestions 
            if s['is_exact'] or s['similarity'] >= 0.4
        ]
        
        return jsonify({
            'suggestions': filtered_suggestions[:5],
            'query': query
        })
        
    except Exception as e:
        print(f"Ошибка получения предложений: {e}")
        return jsonify({'suggestions': []})

@app.route('/api/tags/count', methods=['GET'])
def get_tags_count():
    """Получение количества тегов"""
    try:
        tags_info = get_tags_info()
        return jsonify(tags_info)
    except Exception as e:
        print(f"Ошибка получения количества тегов: {e}")
        return jsonify({
            'total_tags': 0,
            'unique_tags': 0,
            'tags_list': []
        })

@app.route('/api/tags/top', methods=['GET'])
def get_top_tags_route():
    """Получение топ тегов"""
    limit = request.args.get('limit', 20, type=int)
    
    try:
        top_tags = get_top_tags(limit)
        return jsonify({'top_tags': top_tags})
    except Exception as e:
        print(f"Ошибка получения топ тегов: {e}")
        return jsonify({'top_tags': []})

@app.route('/api/sentiment/distribution', methods=['GET'])
def get_sentiment_dist():
    """Получение распределения настроений"""
    try:
        distribution = get_sentiment_distribution()
        return jsonify({'distribution': distribution})
    except Exception as e:
        print(f"Ошибка получения распределения: {e}")
        return jsonify({'distribution': {}})

@app.route('/api/trends/signals', methods=['GET'])
def get_trend_signals_api():
    """Получение активных сигналов из анализатора трендов"""
    try:
        from trend_analyzer import get_trend_signals
        signals = get_trend_signals()
        return jsonify({
            'signals': signals,
            'count': len(signals),
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
    except Exception as e:
        return jsonify({'error': str(e), 'signals': []}), 500

if __name__ == '__main__':
    # Инициализируем БД
    """init_database()
    create_sample_data()"""
    
    # Инициализируем TagSuggester
    tag_suggester.initialize()
    
    # Запускаем сервер
    print("=" * 50)
    print("HR Analytics Dashboard запущен!")
    print("Откройте в браузере: http://localhost:5000")
    print("=" * 50)
    
    app.run(debug=True, host='0.0.0.0', port=5000)
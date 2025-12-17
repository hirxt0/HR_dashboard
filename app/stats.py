"""
stats.py - Модуль для работы со статистикой
"""
import json
from datetime import datetime
from collections import Counter
from typing import Dict, List, Any
from database import get_db_connection

def get_dashboard_stats() -> Dict[str, Any]:
    """Получение статистики для дашборда"""
    conn = get_db_connection()
    
    try:
        # Общая статистика
        cursor = conn.execute("SELECT COUNT(*) as total FROM chunks")
        total_news = cursor.fetchone()['total']
        
        # Собираем все теги
        cursor.execute("SELECT llm_tags FROM chunks WHERE llm_tags IS NOT NULL AND llm_tags != ''")
        all_tags = []
        tag_errors = 0
        
        for row in cursor.fetchall():
            tags_json = row['llm_tags']
            if not tags_json or tags_json.strip() == '':
                continue
                
            try:
                tags = json.loads(tags_json)
                if isinstance(tags, list):
                    all_tags.extend(tags)
                else:
                    tag_errors += 1
            except json.JSONDecodeError:
                tag_errors += 1
            except Exception:
                tag_errors += 1
        
        unique_tags = len(set(all_tags))
        
        # Популярные теги (топ-15)
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
        
        # Форматируем сигналы
        formatted_signals = []
        signal_id = 1
        
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
                
                for i in range(min(3, count)):
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
        
        return {
            'total_news': total_news,
            'unique_tags': unique_tags,
            'total_signals': total_signals,
            'popular_tags': popular_tags,
            'signals': formatted_signals[:6],
            'update_time': datetime.now().strftime('%d.%m.%Y %H:%M'),
            'debug_info': {
                'total_tags_collected': len(all_tags),
                'tag_parsing_errors': tag_errors,
                'tag_samples': list(set(all_tags))[:10] if all_tags else []
            }
        }
        
    except Exception as e:
        print(f"Ошибка получения статистики: {e}")
        import traceback
        traceback.print_exc()
        return {
            'total_news': 0,
            'unique_tags': 0,
            'total_signals': 0,
            'popular_tags': [],
            'signals': [],
            'update_time': datetime.now().strftime('%d.%m.%Y %H:%M'),
            'error': str(e)
        }
    finally:
        conn.close()

def get_sentiment_distribution() -> Dict[str, int]:
    """Получение распределения настроений"""
    conn = get_db_connection()
    
    try:
        cursor = conn.execute('''
        SELECT sentiment, COUNT(*) as count
        FROM chunks 
        WHERE sentiment IS NOT NULL
        GROUP BY sentiment
        ''')
        
        distribution = {}
        for row in cursor.fetchall():
            distribution[row['sentiment']] = row['count']
        
        return distribution
        
    finally:
        conn.close()

def get_top_tags(limit: int = 20) -> List[Dict[str, Any]]:
    """Получение топ тегов"""
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
        
        tag_counter = Counter(all_tags)
        top_tags = [{'tag': tag, 'count': count} 
                   for tag, count in tag_counter.most_common(limit)]
        
        return top_tags
        
    finally:
        conn.close()

def get_tags_info() -> Dict[str, Any]:
    """Получение информации о тегах"""
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
        
        unique_tags = list(set(all_tags))
        
        return {
            'total_tags': len(all_tags),
            'unique_tags': len(unique_tags),
            'tags_list': unique_tags[:50]
        }
        
    finally:
        conn.close()
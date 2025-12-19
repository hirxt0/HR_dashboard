import json
from datetime import datetime
from collections import Counter
from typing import Dict, List, Any
from database import get_db_connection
from trend_analyzer import get_trend_signals  # Импортируем новый модуль
import os

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
        
        # Получаем активные сигналы из анализатора трендов
        active_signals = get_trend_signals()
        
        # Форматируем сигналы для отображения
        formatted_signals = []
        signal_id = 1
        
        for signal in active_signals:
            # Преобразуем тип сигнала в формат для CSS классов
            signal_type_map = {
                'problem': 'problem',
                'growing_problem': 'problem',
                'new_problem': 'problem',
                'opportunity': 'opportunity',
                'growing_opportunity': 'opportunity',
                'new_opportunity': 'opportunity',
                'new_trend': 'early_trend',
                'emerging_trend': 'early_trend'
            }
            
            css_type = signal_type_map.get(signal['type'], 'early_trend')
            
            # Создаем понятное описание с тегом
            tag = signal.get('tag', 'без тега')
            
            # Безопасное получение данных из сигнала
            sentiment = signal.get('sentiment_distribution', {})
            positive = sentiment.get('positive', 0)
            negative = sentiment.get('negative', 0)
            mentions = signal.get('mentions', 0)
            
            # Генерируем описания в зависимости от типа
            descriptions = {
                'problem': f"Тег '{tag}' имеет {negative}% негативных упоминаний ({mentions} всего).",
                'growing_problem': f"⚠️ Нарастающая проблема! Тег '{tag}': {negative}% негатива, рост упоминаний.",
                'new_problem': f"🚨 Новая проблема: тег '{tag}' появился недавно, но уже {negative}% негатива.",
                'opportunity': f"Тег '{tag}' имеет {positive}% позитивных упоминаний ({mentions} всего).",
                'growing_opportunity': f"📈 Растущая возможность! Тег '{tag}': {positive}% позитива, рост интереса.",
                'new_opportunity': f"⭐ Новая возможность: тег '{tag}' быстро набирает популярность с {positive}% позитива.",
                'new_trend': f"🌱 Новый тренд: тег '{tag}' появился недавно ({mentions} упоминаний).",
                'emerging_trend': f"🚀 Зарождающийся тренд: тег '{tag}' быстро растёт ({mentions} упоминаний)."
            }
            
            description = descriptions.get(signal['type'], 
                f"Тег '{tag}': {mentions} упоминаний, {positive}% позитивных, {negative}% негативных.")
            
            formatted_signals.append({
                'id': signal_id,
                'title': signal.get('title', f'Сигнал: {tag}'),
                'description': description,
                'type': css_type,
                'icon': signal.get('icon', 'fas fa-chart-line'),
                'mentions': mentions,
                'trend': signal.get('trend', 'stable'),
                'tag': tag,  # Основной тег
                'sentiment': sentiment,
                'recommendations': signal.get('recommendations', []),
                'priority': signal.get('priority', 50),
                'first_seen': signal.get('first_seen', '?'),
                'last_seen': signal.get('last_seen', '?'),
                'details': {  # Детальная информация для отладки
                    'signal_type': signal.get('type', 'unknown'),
                    'total_mentions': mentions,
                    'sentiment_breakdown': sentiment,
                    'trend_direction': signal.get('trend', 'stable'),
                    'days_active': signal.get('days_active', 'неизвестно')
                }
            })
            signal_id += 1
        
        # Если нет активных сигналов, показываем базовые
        if not formatted_signals:
            formatted_signals = get_basic_signals(conn)
        
        return {
            'total_news': total_news,
            'unique_tags': unique_tags,
            'total_signals': len(active_signals),
            'popular_tags': popular_tags,
            'signals': formatted_signals[:6],  # Максимум 6 сигналов
            'update_time': datetime.now().strftime('%d.%m.%Y %H:%M'),
            'debug_info': {
                'total_tags_collected': len(all_tags),
                'tag_parsing_errors': tag_errors,
                'tag_samples': list(set(all_tags))[:10] if all_tags else [],
                'active_signals_count': len(active_signals)
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

def get_basic_signals(conn) -> List[Dict[str, Any]]:
    """Получение базовых сигналов если анализатор не нашел трендов"""
    print("\n🔍 Запуск get_basic_signals()...")
    
    # Получаем ВСЕ данные сразу для точного подсчета
    cursor = conn.execute('''
    SELECT id, text, llm_tags, sentiment, created_at
    FROM chunks 
    WHERE llm_tags IS NOT NULL AND llm_tags != '' 
    ORDER BY created_at DESC
    ''')
    
    all_rows = cursor.fetchall()
    print(f"📊 Всего записей с тегами: {len(all_rows)}")
    
    # Собираем статистику по тегам
    tag_stats = {}
    
    for row in all_rows:
        tags_json = row['llm_tags']
        sentiment = row['sentiment']
        created_at = row['created_at']
        
        if not tags_json:
            continue
            
        try:
            tags = json.loads(tags_json)
            if not isinstance(tags, list):
                continue
                
            for tag in tags:
                tag = tag.strip()
                if not tag:
                    continue
                    
                if tag not in tag_stats:
                    tag_stats[tag] = {
                        'total': 0, 
                        'positive': 0, 
                        'negative': 0, 
                        'neutral': 0,
                        'dates': []  # Для отслеживания дат
                    }
                
                tag_stats[tag]['total'] += 1
                if sentiment == 'positive':
                    tag_stats[tag]['positive'] += 1
                elif sentiment == 'negative':
                    tag_stats[tag]['negative'] += 1
                elif sentiment == 'neutral':
                    tag_stats[tag]['neutral'] += 1
                
                # Сохраняем дату
                if created_at:
                    tag_stats[tag]['dates'].append(created_at)
                    
        except Exception as e:
            print(f"Ошибка парсинга тегов: {e}")
            continue
    
    print(f"📊 Уникальных тегов найдено: {len(tag_stats)}")
    
    # Форматируем сигналы из реальных тегов
    formatted_signals = []
    signal_id = 1
    
    # Сортируем теги по общему количеству упоминаний
    sorted_tags = sorted(tag_stats.items(), key=lambda x: x[1]['total'], reverse=True)
    
    for tag, stats in sorted_tags[:15]:  # Берем топ-15 по упоминаниям
        total = stats['total']
        
        if total < 3:  # Слишком мало данных
            continue
            
        positive_pct = (stats['positive'] / total * 100) if total > 0 else 0
        negative_pct = (stats['negative'] / total * 100) if total > 0 else 0
        neutral_pct = (stats['neutral'] / total * 100) if total > 0 else 0
        
        print(f"  📈 Тег '{tag}': {total} уп., поз={positive_pct:.1f}%, нег={negative_pct:.1f}%, нейтр={neutral_pct:.1f}%")
        
        # Определяем тип сигнала (более мягкие критерии)
        signal_type = None
        title = f'Тренд: {tag}'
        description = f'Активная тема: {total} упоминаний'
        icon = 'fas fa-chart-line'
        priority = 50
        trend = 'stable'
        
        if negative_pct > 40 and total >= 5:  # Понижен порог с 50% до 40%
            signal_type = 'problem'
            title = f'Проблема: {tag}'
            description = f'Преобладает негатив ({negative_pct:.1f}% из {total} упоминаний)'
            icon = 'fas fa-exclamation-triangle'
            priority = 70 + min(20, negative_pct // 5)
            trend = 'up' if negative_pct > 50 else 'stable'
        elif positive_pct > 40 and total >= 5:  # Понижен порог с 50% до 40%
            signal_type = 'opportunity'
            title = f'Возможность: {tag}'
            description = f'Преобладает позитив ({positive_pct:.1f}% из {total} упоминаний)'
            icon = 'fas fa-lightbulb'
            priority = 65 + min(20, positive_pct // 5)
            trend = 'up' if positive_pct > 50 else 'stable'
        elif total >= 5:  # Популярный тег
            signal_type = 'early_trend'
            title = f'Тренд: {tag}'
            description = f'Популярная тема: {total} упоминаний'
            icon = 'fas fa-chart-line'
            priority = 50 + min(10, total // 2)
        
        if not signal_type:
            continue
        
        # Определяем даты
        dates = stats.get('dates', [])
        if dates:
            dates.sort()
            first_seen = dates[0][:10] if dates[0] else 'неизвестно'
            last_seen = dates[-1][:10] if dates[-1] else 'недавно'
            
            # Форматируем даты в русский формат
            try:
                if first_seen != 'неизвестно':
                    dt = datetime.strptime(first_seen, '%Y-%m-%d')
                    first_seen = dt.strftime('%d.%m.%Y')
                if last_seen != 'недавно':
                    dt = datetime.strptime(last_seen, '%Y-%m-%d')
                    last_seen = dt.strftime('%d.%m.%Y')
            except:
                pass
        else:
            first_seen = 'неизвестно'
            last_seen = 'недавно'
        
        # Получаем рекомендации
        recommendations = []
        if signal_type == 'problem':
            recommendations.append(f'Проанализировать причины негатива по теме "{tag}"')
            recommendations.append('Разработать план коммуникации')
        elif signal_type == 'opportunity':
            recommendations.append(f'Использовать позитивный тренд по теме "{tag}"')
            recommendations.append('Рассмотреть возможности развития')
        else:
            recommendations.append(f'Установить мониторинг темы "{tag}"')
        
        formatted_signals.append({
            'id': signal_id,
            'title': title,
            'description': description,
            'type': signal_type,
            'icon': icon,
            'mentions': total,
            'trend': trend,
            'tag': tag,
            'sentiment': {
                'positive': round(positive_pct, 1),
                'negative': round(negative_pct, 1),
                'neutral': round(neutral_pct, 1)
            },
            'recommendations': recommendations,
            'priority': priority,
            'first_seen': first_seen,
            'last_seen': last_seen,
            'debug': {
                'raw_total': total,
                'raw_positive': stats['positive'],
                'raw_negative': stats['negative'],
                'raw_neutral': stats['neutral']
            }
        })
        signal_id += 1
        
        if len(formatted_signals) >= 6:  # До 6 сигналов
            break
    
    # Сортируем по приоритету
    formatted_signals.sort(key=lambda x: x['priority'], reverse=True)
    
    print(f"📈 Создано базовых сигналов: {len(formatted_signals)}")
    
    # Если все еще нет сигналов, создаем общие по настроениям
    if not formatted_signals:
        print("⚠️ Нет подходящих тегов, создаем общие сигналы...")
        cursor = conn.execute('''
        SELECT sentiment, COUNT(*) as count
        FROM chunks 
        WHERE sentiment IS NOT NULL
        GROUP BY sentiment
        ''')
        
        sentiments = cursor.fetchall()
        
        for row in sentiments:
            sentiment = row['sentiment']
            count = row['count']
            
            if count < 5:
                continue
                
            signal_types = {
                'negative': {
                    'type': 'problem',
                    'title': 'Общий негативный фон',
                    'icon': 'fas fa-exclamation-triangle',
                    'description': f'Высокий уровень негативных новостей ({count})',
                    'tag': 'негативный фон',
                    'priority': 60
                },
                'positive': {
                    'type': 'opportunity',
                    'title': 'Общий позитивный фон',
                    'icon': 'fas fa-lightbulb',
                    'description': f'Преобладают позитивные новости ({count})',
                    'tag': 'позитивный фон',
                    'priority': 55
                },
                'neutral': {
                    'type': 'early_trend',
                    'title': 'Нейтральный фон',
                    'icon': 'fas fa-chart-line',
                    'description': f'Много нейтральных новостей ({count})',
                    'tag': 'нейтральный фон',
                    'priority': 50
                }
            }
            
            if sentiment in signal_types:
                signal_info = signal_types[sentiment]
                
                sentiment_dist = {'positive': 0, 'negative': 0, 'neutral': 0}
                sentiment_dist[sentiment] = 100
                
                formatted_signals.append({
                    'id': signal_id,
                    'title': title,
                    'description': description,
                    'type': signal_type,
                    'icon': icon,
                    'mentions': total,
                    'trend': trend,
                    'tag': tag,
                    'sentiment': {
                        'positive': round(positive_pct, 1),
                        'negative': round(negative_pct, 1),
                        'neutral': round(neutral_pct, 1)
                    },
                    # Добавьте вызов генерации рекомендаций через LLM
                    'recommendations': self._get_llm_recommendations(tag, signal_type, positive_pct, negative_pct, total),
                    'priority': priority,
                    'first_seen': first_seen,
                    'last_seen': last_seen,
                    'debug': {
                        'raw_total': total,
                        'raw_positive': stats['positive'],
                        'raw_negative': stats['negative'],
                        'raw_neutral': stats['neutral']
                    }
                })
                signal_id += 1
        
        # Берем максимум 2 общих сигнала
        formatted_signals = formatted_signals[:2]
    
    return formatted_signals[:3]  # Максимум 3 сигнала

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

def _get_llm_recommendations(self, tag: str, signal_type: str, 
                            positive_pct: float, negative_pct: float, 
                            total: int) -> List[str]:
    """Получить рекомендации от LLM"""
    try:
        from classifier import LLMMetadataClassifier
        classifier = LLMMetadataClassifier(api_key=os.getenv("GROQ_API_KEY"))
        
        sentiment_distribution = {
            'positive': round(positive_pct, 1),
            'negative': round(negative_pct, 1),
            'neutral': round(100 - positive_pct - negative_pct, 1)
        }
        
        trend = 'up' if positive_pct > negative_pct else 'down'
        
        recommendations = classifier.generate_recommendations(
            tag=tag,
            signal_type=signal_type,
            sentiment_distribution=sentiment_distribution,
            mentions_count=total,
            trend=trend
        )
        
        return recommendations[:3] if recommendations else []
        
    except Exception as e:
        print(f"❌ Ошибка получения рекомендаций от LLM: {e}")
        return [f"Проанализировать тему '{tag}'", "Установить мониторинг"]
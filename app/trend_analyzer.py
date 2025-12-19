
"""
trend_analyzer.py - Анализ трендов на основе тегов и настроений
"""
import json
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from typing import Dict, List, Any, Tuple
from database import get_db_connection
from classifier import LLMMetadataClassifier
import os

class TrendAnalyzer:
    def __init__(self):
        self.conn = get_db_connection()
    
    def analyze_tag_trends(self, days_back: int = 30) -> Dict[str, Any]:
        """Анализ трендов по тегам за последние N дней"""
        
        try:
            # Получаем дату начала периода
            start_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
            
            # Получаем все новости за период
            cursor = self.conn.execute('''
                SELECT id, text, metadata, llm_tags, sentiment, created_at
                FROM chunks
                WHERE date(created_at) >= date(?)
                ORDER BY created_at
            ''', (start_date,))
            
            news_items = cursor.fetchall()
            
            # Структуры для анализа
            tag_stats = defaultdict(lambda: {
                'total': 0,
                'positive': 0,
                'negative': 0,
                'neutral': 0,
                'by_day': defaultdict(lambda: {'total': 0, 'positive': 0, 'negative': 0, 'neutral': 0}),
                'first_seen': None,
                'last_seen': None
            })
            
            # Обрабатываем каждую новость
            for item in news_items:
                try:
                    date_str = item['created_at'][:10]  # YYYY-MM-DD
                    sentiment = item['sentiment']
                    
                    # Парсим теги
                    tags = []
                    if item['llm_tags']:
                        try:
                            tags = json.loads(item['llm_tags'])
                        except:
                            pass
                    
                    for tag in tags:
                        tag = tag.strip()
                        if not tag:
                            continue
                            
                        stats = tag_stats[tag]
                        stats['total'] += 1
                        
                        if sentiment == 'positive':
                            stats['positive'] += 1
                            stats['by_day'][date_str]['positive'] += 1
                        elif sentiment == 'negative':
                            stats['negative'] += 1
                            stats['by_day'][date_str]['negative'] += 1
                        elif sentiment == 'neutral':
                            stats['neutral'] += 1
                            stats['by_day'][date_str]['neutral'] += 1
                        
                        stats['by_day'][date_str]['total'] += 1
                        
                        # Обновляем даты
                        if not stats['first_seen'] or date_str < stats['first_seen']:
                            stats['first_seen'] = date_str
                        if not stats['last_seen'] or date_str > stats['last_seen']:
                            stats['last_seen'] = date_str
                            
                except Exception as e:
                    print(f"Ошибка обработки новости {item['id']}: {e}")
                    continue
            
            # Анализируем каждый тег
            signals = []
            
            for tag, stats in tag_stats.items():
                if stats['total'] < 3:  # Слишком мало данных для анализа
                    continue
                
                # Рассчитываем проценты
                total = stats['total']
                positive_pct = (stats['positive'] / total * 100) if total > 0 else 0
                negative_pct = (stats['negative'] / total * 100) if total > 0 else 0
                neutral_pct = (stats['neutral'] / total * 100) if total > 0 else 0
                
                # Анализируем распределение по дням для определения тренда
                days_data = list(stats['by_day'].items())
                days_data.sort()  # Сортируем по дате
                
                if len(days_data) < 3:  # Нужно минимум 3 дня для анализа тренда
                    trend = 'stable'
                else:
                    # Анализируем последние 7 дней
                    recent_days = days_data[-7:]
                    if len(recent_days) >= 3:
                        # Считаем среднее количество новостей в первой и второй половине периода
                        mid = len(recent_days) // 2
                        # ИСПРАВЛЕНИЕ: берем второй элемент кортежа (stats_dict)
                        first_half = sum(d[1]['total'] for d in recent_days[:mid])
                        second_half = sum(d[1]['total'] for d in recent_days[mid:])

                        if second_half > first_half * 1.5:  # Рост более 50%
                            trend = 'up'
                        elif second_half < first_half * 0.7:  # Падение более 30%
                            trend = 'down'
                        else:
                            trend = 'stable'
                    else:
                        trend = 'stable'
                
                # Определяем тип сигнала
                signal_type = self._determine_signal_type(
                    positive_pct, negative_pct, total, trend, days_data
                )
                
                if signal_type:
                    signal = self._create_signal(
                        tag, signal_type, stats, 
                        positive_pct, negative_pct, 
                        total, trend, days_data
                    )
                    if signal:
                        signals.append(signal)
            
            # Сортируем сигналы по важности
            signals.sort(key=lambda x: x.get('priority', 0), reverse=True)
            
            return {
                'signals': signals[:10],  # Топ 10 сигналов
                'total_tags_analyzed': len(tag_stats),
                'period_days': days_back,
                'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
        except Exception as e:
            print(f"Ошибка анализа трендов: {e}")
            import traceback
            traceback.print_exc()
            return {
                'signals': [],
                'error': str(e)
            }
        finally:
            self.conn.close()
    
    # trend_analyzer.py - исправленная функция
    def _determine_signal_type(self, positive_pct: float, negative_pct: float, 
                               total: int, trend: str, days_data: List[Tuple[str, Dict]]) -> str:
        """Определение типа сигнала на основе анализа"""

        if total < 5:  # Мало данных
            return None

        # Критерии для разных типов сигналов
        if negative_pct > 60 and total >= 10:
            if trend == 'up':
                return 'growing_problem'  # Нарастающая проблема
            else:
                return 'problem'  # Стабильная проблема

        if positive_pct > 60 and total >= 8:
            if trend == 'up':
                return 'growing_opportunity'  # Растущая возможность
            else:
                return 'opportunity'  # Стабильная возможность

        # Новый тренд (тег появился недавно и быстро набирает)
        if len(days_data) > 0:
            first_date_str = days_data[0][0]
            last_date_str = days_data[-1][0]
            try:
                first_date = datetime.strptime(first_date_str, '%Y-%m-%d')
                last_date = datetime.strptime(last_date_str, '%Y-%m-%d')
                days_active = (last_date - first_date).days + 1

                if days_active <= 7 and total >= 5:  # Появился за неделю и уже 5+ упоминаний
                    if positive_pct > 50:
                        return 'new_opportunity'  # Новая возможность
                    elif negative_pct > 50:
                        return 'new_problem'  # Новая проблема
                    else:
                        return 'new_trend'  # Новый нейтральный тренд
            except:
                pass
            
        # Резкий рост/падение
        if len(days_data) >= 7:
            recent = days_data[-7:]
            if len(recent) >= 4:
                # Берем второй элемент кортежа (stats_dict)
                recent_counts = [d[1]['total'] for d in recent]
                if len(recent_counts) >= 2:
                    avg_first = sum(recent_counts[:len(recent_counts)//2]) / (len(recent_counts)//2)
                    avg_second = sum(recent_counts[len(recent_counts)//2:]) / (len(recent_counts)//2)

                    if avg_second > avg_first * 2:  # Рост в 2 раза
                        if positive_pct > 40:
                            return 'growing_opportunity'
                        elif negative_pct > 40:
                            return 'growing_problem'
                        else:
                            return 'emerging_trend'

        return None
        
        # Резкий рост/падение
        if len(days_data) >= 7:
            recent = days_data[-7:]
            if len(recent) >= 4:
                # ИСПРАВЛЕНИЕ: берем второй элемент кортежа
                recent_counts = [d[1]['total'] for d in recent]
                avg_first = sum(recent_counts[:len(recent_counts)//2]) / (len(recent_counts)//2)
                avg_second = sum(recent_counts[len(recent_counts)//2:]) / (len(recent_counts)//2)

                if avg_second > avg_first * 2:  # Рост в 2 раза
                    if positive_pct > 40:
                        return 'growing_opportunity'
                    elif negative_pct > 40:
                        return 'growing_problem'
                    else:
                        return 'emerging_trend'
        
        return None
    
    def _create_signal(self, tag: str, signal_type: str, stats: Dict, 
                      positive_pct: float, negative_pct: float, 
                      total: int, trend: str, days_data: List[Tuple[str, Dict]]) -> Dict[str, Any]:
    
        """Создание объекта сигнала"""
        
        # Форматируем даты
        first_seen = stats.get('first_seen', '')
        last_seen = stats.get('last_seen', '')
        
        if first_seen:
            try:
                # Преобразуем YYYY-MM-DD в DD.MM.YYYY
                date_obj = datetime.strptime(first_seen, '%Y-%m-%d')
                first_seen_formatted = date_obj.strftime('%d.%m.%Y')
            except:
                first_seen_formatted = first_seen
        else:
            first_seen_formatted = 'неизвестно'
            
        if last_seen:
            try:
                date_obj = datetime.strptime(last_seen, '%Y-%m-%d')
                last_seen_formatted = date_obj.strftime('%d.%m.%Y')
            except:
                last_seen_formatted = last_seen
        else:
            last_seen_formatted = 'недавно'
        
        # Базовая информация
        signal = {
            'tag': tag,
            'type': signal_type,
            'mentions': total,
            'trend': trend,
            'sentiment_distribution': {
                'positive': round(positive_pct, 1),
                'negative': round(negative_pct, 1),
                'neutral': round(100 - positive_pct - negative_pct, 1)
            },
            'first_seen': first_seen_formatted,  # Форматированная дата
            'last_seen': last_seen_formatted     # Форматированная дата
        }

        # Базовая информация
        signal = {
            'tag': tag,
            'type': signal_type,
            'mentions': total,
            'trend': trend,
            'sentiment_distribution': {
                'positive': round(positive_pct, 1),
                'negative': round(negative_pct, 1),
                'neutral': round(100 - positive_pct - negative_pct, 1)
            },
            'first_seen': stats['first_seen'],
            'last_seen': stats['last_seen']
        }
        
        # Настраиваем в зависимости от типа
        type_config = {
            'problem': {
                'title': f'Проблема: {tag}',
                'description': f'Высокий уровень негативных упоминаний ({negative_pct:.1f}%). Требует внимания.',
                'icon': 'fas fa-exclamation-triangle',
                'priority': 80,
                'color': 'danger'
            },
            'growing_problem': {
                'title': f'Нарастающая проблема: {tag}',
                'description': f'Негативные упоминания растут ({negative_pct:.1f}%). Необходимо срочное вмешательство.',
                'icon': 'fas fa-fire',
                'priority': 95,
                'color': 'danger'
            },
            'opportunity': {
                'title': f'Возможность: {tag}',
                'description': f'Высокий уровень позитивных упоминаний ({positive_pct:.1f}%). Потенциал для развития.',
                'icon': 'fas fa-lightbulb',
                'priority': 70,
                'color': 'success'
            },
            'growing_opportunity': {
                'title': f'Растущая возможность: {tag}',
                'description': f'Позитивные упоминания быстро растут ({positive_pct:.1f}%). Отличный потенциал.',
                'icon': 'fas fa-rocket',
                'priority': 85,
                'color': 'success'
            },
            'new_opportunity': {
                'title': f'Новая возможность: {tag}',
                'description': f'Новый тренд с позитивным настроением. {total} упоминаний за неделю.',
                'icon': 'fas fa-star',
                'priority': 90,
                'color': 'success'
            },
            'new_problem': {
                'title': f'Новая проблема: {tag}',
                'description': f'Новый тренд с негативным настроением. {total} упоминаний за неделю.',
                'icon': 'fas fa-bolt',
                'priority': 88,
                'color': 'danger'
            },
            'new_trend': {
                'title': f'Новый тренд: {tag}',
                'description': f'Новая тема с {total} упоминаниями за неделю. Требует мониторинга.',
                'icon': 'fas fa-eye',
                'priority': 60,
                'color': 'warning'
            },
            'emerging_trend': {
                'title': f'Зарождающийся тренд: {tag}',
                'description': f'Быстрый рост упоминаний ({trend} тренд). {total} упоминаний всего.',
                'icon': 'fas fa-seedling',
                'priority': 75,
                'color': 'info'
            }
        }
        
        config = type_config.get(signal_type, {
            'title': f'Тренд: {tag}',
            'description': f'Активность по тегу: {total} упоминаний.',
            'icon': 'fas fa-chart-line',
            'priority': 50,
            'color': 'info'
        })
        
        signal.update(config)
        
        # Добавляем рекомендации
        signal['recommendations'] = self._generate_recommendations(signal_type, tag, positive_pct, negative_pct)
        
        return signal
    
    def _generate_recommendations(self, signal_type: str, tag: str, 
                                 positive_pct: float, negative_pct: float) -> List[str]:
        """Генерация рекомендаций на основе типа сигнала с использованием LLM"""

        # Создаем экземпляр классификатора для использования LLM
        try:
            from classifier import LLMMetadataClassifier
            classifier = LLMMetadataClassifier(api_key=os.getenv("GROQ_API_KEY"))

            sentiment_distribution = {
                'positive': round(positive_pct, 1),
                'negative': round(negative_pct, 1),
                'neutral': round(100 - positive_pct - negative_pct, 1)
            }

            # Определяем тренд на основе процентов
            if positive_pct > negative_pct:
                trend = 'up' if positive_pct > 55 else 'stable'
            else:
                trend = 'down' if negative_pct > 55 else 'stable'

            # Получаем рекомендации от LLM
            recommendations = classifier.generate_recommendations(
                tag=tag,
                signal_type=signal_type,
                sentiment_distribution=sentiment_distribution,
                mentions_count=0,  # Будет установлено позже
                trend=trend
            )

            if recommendations and len(recommendations) >= 2:
                print(f"🤖 LLM сгенерировал {len(recommendations)} рекомендаций для '{tag}'")
                return recommendations[:3]  # Берем топ-3 рекомендации

        except Exception as e:
            print(f"❌ Ошибка генерации рекомендаций через LLM: {e}")

        # Резервные рекомендации если LLM не сработал
        recommendations = []

        if 'problem' in signal_type:
            if negative_pct > 70:
                recommendations.append(f'Срочно проанализировать причины негатива по теме "{tag}"')
                recommendations.append('Разработать план коммуникации для снижения негатива')
            else:
                recommendations.append(f'Мониторить ситуацию по теме "{tag}"')
                recommendations.append('Провести анализ источников негативных упоминаний')

        elif 'opportunity' in signal_type:
            if positive_pct > 70:
                recommendations.append(f'Использовать позитивный тренд по теме "{tag}" в маркетинге')
                recommendations.append('Рассмотреть возможность инвестиций в данное направление')
            else:
                recommendations.append(f'Усилить активность по теме "{tag}"')
                recommendations.append('Изучить успешные кейсы по данной теме')

        elif 'new' in signal_type or 'emerging' in signal_type:
            recommendations.append(f'Установить регулярный мониторинг темы "{tag}"')
            recommendations.append('Проанализировать ранние признаки тренда')
            recommendations.append('Разработать стратегию реагирования')

        # Общие рекомендации
        if not recommendations:
            recommendations.append(f'Проанализировать активность по теме "{tag}"')

        recommendations.append('Обновить анализ через 3 дня для отслеживания динамики')

        return recommendations[:4]  # Максимум 4 рекомендации


def get_trend_signals() -> List[Dict[str, Any]]:
    """Получение активных сигналов для дашборда"""
    analyzer = TrendAnalyzer()
    result = analyzer.analyze_tag_trends(days_back=30)
    
    if 'signals' in result and result['signals']:
        return result['signals'][:6]  # Берем топ-6 сигналов
    
    return []
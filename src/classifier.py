from metadata_processor import MetadataProcessorRU
from tg_parser import TelegramDatabase
from typing import List, Dict
from tqdm import tqdm
import json


class MessageClassifier:
    """
    Классификатор сообщений с интеграцией БД
    """
    
    def __init__(self, db_path: str = "telegram_data.db"):
        self.db = TelegramDatabase(db_path)
        
        print(" Инициализация классификатора...")
        self.processor = MetadataProcessorRU()
        print(" Классификатор готов!\n")
    
    def process_message(self, message: Dict) -> Dict:
        """
        Обработка одного сообщения
        Возвращает метаданные
        """
        # Используем очищенный текст если есть, иначе оригинальный
        text = message.get('text_cleaned') or message.get('text', '')
        
        if not text or len(text) < 20:
            return self._get_empty_metadata()
        
        try:
            # Извлекаем теги
            tags = self.processor.extract_tags(text, top_n=5)
            
            # Анализ тональности
            sentiment_data = self.processor.analyze_sentiment(text)
            
            # Классификация темы
            topic_analysis = self.processor.classify_topic(text, tags)
            
            # Детекция инсайдов
            insider_data = self.processor.detect_insider(text)
            
            return {
                'tags': tags,
                'sentiment': sentiment_data['sentiment'],
                'sentiment_score': sentiment_data['score'],
                'category': topic_analysis['main_topic'],
                'topic_scores': topic_analysis['scores'],
                'topic_details': topic_analysis.get('details', {}),
                'is_insider': insider_data['is_insider'],
                'insider_confidence': insider_data['confidence']
            }
            
        except Exception as e:
            print(f" Ошибка обработки: {e}")
            return self._get_empty_metadata()
    
    def _get_empty_metadata(self) -> Dict:
        """Метаданные по умолчанию"""
        return {
            'tags': [],
            'sentiment': 'neutral',
            'sentiment_score': 0.0,
            'category': 'общее',
            'topic_scores': {},
            'topic_details': {},
            'is_insider': False,
            'insider_confidence': 0.0
        }
    
    def process_unprocessed_messages(self, batch_size: int = 50, limit: int = None):
        """
        Обработка всех необработанных сообщений из БД
        """
        print("КЛАССИФИКАЦИЯ СООБЩЕНИЙ")

        
        # Получаем необработанные сообщения
        messages = self.db.get_unprocessed_messages(limit=limit)
        
        if not messages:
            print("✅ Все сообщения уже обработаны!")
            return
        
        print(f" Найдено необработанных сообщений: {len(messages)}")
        print(f" Начинаем обработку...\n")
        
        processed_count = 0
        error_count = 0
        
        # Статистика для отчёта
        category_stats = {}
        sentiment_stats = {'positive': 0, 'neutral': 0, 'negative': 0}
        all_tags = []
        
        for i in tqdm(range(0, len(messages), batch_size), desc="Обработка"):
            batch = messages[i:i + batch_size]
            
            for message in batch:
                try:
                    # Классификация
                    metadata = self.process_message(message)
                    
                    # Сохранение в БД
                    self.db.insert_metadata(message['id'], metadata)
                    
                    # Статистика
                    processed_count += 1
                    category = metadata['category']
                    category_stats[category] = category_stats.get(category, 0) + 1
                    sentiment_stats[metadata['sentiment']] += 1
                    all_tags.extend(metadata['tags'])
                    
                except Exception as e:
                    error_count += 1
                    print(f"\n Ошибка обработки сообщения {message['id']}: {e}")
        
        # Итоговая статистика
        self._print_processing_stats(
            processed_count, 
            error_count, 
            category_stats, 
            sentiment_stats, 
            all_tags
        )
    
    def _print_processing_stats(self, processed: int, errors: int, 
                               categories: Dict, sentiments: Dict, tags: List):
        """Вывод статистики обработки"""
        from collections import Counter
        
        print("СТАТИСТИКА ОБРАБОТКИ")
        
        print(f"\n✅ Обработано: {processed}")
        print(f" Ошибок: {errors}")
        
        # Категории
        print(f"\n Распределение по категориям:")
        for cat in sorted(categories.keys(), key=lambda x: categories[x], reverse=True):
            count = categories[cat]
            percentage = (count / processed) * 100 if processed > 0 else 0
            print(f"  • {cat:20s}: {count:4d} ({percentage:5.1f}%)")
        
        # Тональность
        print(f"\n Распределение по тональности:")
        for sent, count in sentiments.items():
            percentage = (count / processed) * 100 if processed > 0 else 0
            print(f"  • {sent:20s}: {count:4d} ({percentage:5.1f}%)")
        
        # Топ теги
        if tags:
            tag_counts = Counter(tags)
            print(f"\n Топ-15 тегов:")
            for tag, count in tag_counts.most_common(15):
                print(f"  • {tag:25s}: {count}")
        
    
    def search_by_tags(self, query_tags: List[str], limit: int = 10) -> List[Dict]:
        """
        Поиск сообщений по тегам
        Возвращает сообщения с метаданными
        """
        results = self.db.search_by_tags(query_tags, limit=limit)
        
        # Парсим JSON поля
        for r in results:
            try:
                r['tags'] = json.loads(r['tags']) if r.get('tags') else []
                r['topic_scores'] = json.loads(r['topic_scores']) if r.get('topic_scores') else {}
            except:
                pass
        
        return results
    
    def get_category_distribution(self) -> Dict:
        """Статистика по категориям"""
        cursor = self.db.conn.cursor()
        cursor.execute('''
            SELECT category, COUNT(*) as count
            FROM message_metadata
            WHERE category IS NOT NULL
            GROUP BY category
            ORDER BY count DESC
        ''')
        return {row[0]: row[1] for row in cursor.fetchall()}
    
    def get_sentiment_distribution(self) -> Dict:
        """Статистика по тональности"""
        cursor = self.db.conn.cursor()
        cursor.execute('''
            SELECT sentiment, COUNT(*) as count
            FROM message_metadata
            WHERE sentiment IS NOT NULL
            GROUP BY sentiment
            ORDER BY count DESC
        ''')
        return {row[0]: row[1] for row in cursor.fetchall()}
    
    def get_insider_messages(self, min_confidence: float = 0.5, limit: int = 20) -> List[Dict]:
        """Получить инсайдерские сообщения"""
        cursor = self.db.conn.cursor()
        cursor.execute('''
            SELECT m.*, mm.*
            FROM messages m
            JOIN message_metadata mm ON m.id = mm.message_id
            WHERE mm.is_insider = 1 AND mm.insider_confidence >= ?
            ORDER BY mm.insider_confidence DESC
            LIMIT ?
        ''', (min_confidence, limit))
        
        results = [dict(row) for row in cursor.fetchall()]
        
        # Парсим JSON
        for r in results:
            try:
                r['tags'] = json.loads(r['tags']) if r.get('tags') else []
            except:
                pass
        
        return results
    
    def export_to_json(self, output_path: str, limit: int = None):
        """Экспорт данных в JSON"""
        cursor = self.db.conn.cursor()
        
        query = '''
            SELECT m.*, mm.*
            FROM messages m
            JOIN message_metadata mm ON m.id = mm.message_id
            ORDER BY m.datetime DESC
        '''
        
        if limit:
            query += f' LIMIT {limit}'
        
        cursor.execute(query)
        results = [dict(row) for row in cursor.fetchall()]
        
        # Парсим JSON поля
        for r in results:
            try:
                r['tags'] = json.loads(r['tags']) if r.get('tags') else []
                r['topic_scores'] = json.loads(r['topic_scores']) if r.get('topic_scores') else {}
            except:
                pass
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f" Данные экспортированы: {output_path}")
    
    def close(self):
        """Закрытие соединения с БД"""
        self.db.close()


# Пример использования
if __name__ == "__main__":
    classifier = MessageClassifier("telegram_data.db")
    
    # Обработка всех необработанных сообщений
    classifier.process_unprocessed_messages(batch_size=50, limit=100)
    
    # Статистика
    print("\n📊 ОБЩАЯ СТАТИСТИКА:")
    print(f"\nКатегории:")
    for cat, count in classifier.get_category_distribution().items():
        print(f"  • {cat}: {count}")
    
    print(f"\nТональность:")
    for sent, count in classifier.get_sentiment_distribution().items():
        print(f"  • {sent}: {count}")
    
    # Поиск по тегам
    print("\n🔍 ПОИСК ПО ТЕГАМ ['искусственный', 'интеллект']:")
    results = classifier.search_by_tags(['искусственный', 'интеллект'], limit=3)
    for r in results:
        print(f"\n[{r['channel']}] {r['datetime']}")
        print(f"Категория: {r['category']} | Тональность: {r['sentiment']}")
        print(f"Теги: {', '.join(r['tags'][:5])}")
        print(f"{r['text'][:150]}...")
    
    # Инсайды
    insiders = classifier.get_insider_messages(min_confidence=0.5, limit=5)
    if insiders:
        print(f"\n🔒 ИНСАЙДЕРСКАЯ ИНФОРМАЦИЯ ({len(insiders)} сообщений):")
        for ins in insiders:
            print(f"\n[{ins['channel']}] Уверенность: {ins['insider_confidence']:.0%}")
            print(f"{ins['text'][:150]}...")
    
    # Экспорт
    classifier.export_to_json("classified_messages.json", limit=1000)
    
    classifier.close()
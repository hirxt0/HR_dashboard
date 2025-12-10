from typing import List, Dict
import json
from tqdm import tqdm

# Импортируем новый процессор метаданных
try:
    from metadata_processor import MetadataProcessorRU
    METADATA_PROCESSOR_AVAILABLE = True
except ImportError:
    METADATA_PROCESSOR_AVAILABLE = False
    print("⚠️ MetadataProcessorRU не найден, используем базовый классификатор")


class Classifier:
    """
    Классификатор чанков с поддержкой продвинутой обработки метаданных
    """
    
    def __init__(self, cfg, llm=None):
        self.cfg = cfg
        self.llm = llm
        self.mode = cfg["llm"].get("mode", "mock")
        
        # Инициализируем MetadataProcessorRU если доступен
        self.metadata_processor = None
        if METADATA_PROCESSOR_AVAILABLE:
            try:
                print(" Инициализация MetadataProcessorRU...")
                self.metadata_processor = MetadataProcessorRU()
                print(" MetadataProcessorRU готов к работе!")
            except Exception as e:
                print(f" Ошибка инициализации MetadataProcessorRU: {e}")
                print("Переключаюсь на базовый классификатор")

    def classify_chunks(self, chunks: List[Dict]) -> List[Dict]:
        """
        Классифицирует список чанков, добавляя метаданные
        """
        print("КЛАССИФИКАЦИЯ ЧАНКОВ")
        print(f"Режим: {'MetadataProcessorRU' if self.metadata_processor else 'Mock'}")
        print(f"Количество чанков: {len(chunks)}")
        print(f"{'='*60}\n")
        
        if self.metadata_processor:
            return self._classify_with_metadata_processor(chunks)
        else:
            return self._classify_mock(chunks)

    def _classify_with_metadata_processor(self, chunks: List[Dict]) -> List[Dict]:
        """
        Классификация с использованием MetadataProcessorRU
        """
        batch_size = 50
        results = []
        
        for i in tqdm(range(0, len(chunks), batch_size), desc="Классификация"):
            batch = chunks[i:i + batch_size]
            
            for chunk in batch:
                try:
                    # Обрабатываем чанк через MetadataProcessorRU
                    result = self.metadata_processor.process_chunk(
                        chunk_id=chunk.get('chunk_id', f'chunk_{i}'),
                        text=chunk['text']
                    )
                    
                    # Добавляем метаданные к чанку
                    chunk['meta'] = {
                        'tags': result['metadata']['tags'],
                        'sentiment': result['metadata']['sentiment'],
                        'sentiment_score': result['metadata']['sentiment_score'],
                        'category': result['metadata']['topic'],
                        'topic_scores': result['metadata']['topic_scores'],
                        'topic_details': result['metadata']['topic_details'],
                        'is_insider': result['metadata']['is_insider'],
                        'insider_confidence': result['metadata']['insider_confidence']
                    }
                    
                    results.append(chunk)
                    
                except Exception as e:
                    print(f" Ошибка обработки чанка {chunk.get('chunk_id')}: {e}")
                    # Добавляем чанк без метаданных
                    chunk['meta'] = self._get_fallback_meta()
                    results.append(chunk)
        
        # Статистика
        self._print_classification_stats(results)
        
        return results

    def _classify_mock(self, chunks: List[Dict]) -> List[Dict]:
        """
        Mock-классификация (старый метод)
        """
        import random
        
        categories = ["технологии", "бизнес", "политика", "наука", "общее"]
        sentiments = ["positive", "neutral", "negative"]
        
        for chunk in tqdm(chunks, desc="Mock классификация"):
            chunk['meta'] = {
                'category': random.choice(categories),
                'tags': [f"tag_{i}" for i in range(3)],
                'sentiment': random.choice(sentiments),
                'sentiment_score': random.random(),
                'is_insider': False,
                'insider_confidence': 0.0
            }
        
        return chunks

    def _get_fallback_meta(self) -> Dict:
        """
        Метаданные по умолчанию при ошибке
        """
        return {
            'category': 'общее',
            'tags': [],
            'sentiment': 'neutral',
            'sentiment_score': 0.0,
            'is_insider': False,
            'insider_confidence': 0.0
        }

    def _print_classification_stats(self, chunks: List[Dict]):
        """
        Выводит статистику классификации
        """
        from collections import Counter
        
        print("СТАТИСТИКА КЛАССИФИКАЦИИ")
        
        # Статистика по категориям
        categories = [c['meta'].get('category', 'unknown') for c in chunks]
        cat_counts = Counter(categories)
        
        print("\n Распределение по категориям:")
        for cat, count in cat_counts.most_common():
            percentage = (count / len(chunks)) * 100
            print(f"  • {cat:20s}: {count:3d} ({percentage:5.1f}%)")
        
        # Статистика по тональности
        sentiments = [c['meta'].get('sentiment', 'unknown') for c in chunks]
        sent_counts = Counter(sentiments)
        
        print("\n Распределение по тональности:")
        for sent, count in sent_counts.most_common():
            percentage = (count / len(chunks)) * 100
            print(f"  • {sent:20s}: {count:3d} ({percentage:5.1f}%)")
        
        # Инсайдеры
        insiders = [c for c in chunks if c['meta'].get('is_insider', False)]
        if insiders:
            print(f"\n Инсайдерская информация: {len(insiders)} чанков")
            avg_confidence = sum(c['meta'].get('insider_confidence', 0) for c in insiders) / len(insiders)
            print(f"  Средняя уверенность: {avg_confidence:.2%}")
        
        # Самые частые теги
        all_tags = []
        for c in chunks:
            all_tags.extend(c['meta'].get('tags', []))
        
        if all_tags:
            tag_counts = Counter(all_tags)
            print("\n Топ-10 тегов:")
            for tag, count in tag_counts.most_common(10):
                print(f"  • {tag:20s}: {count}")
        
        print(f"\n{'='*60}\n")

    def save_classification_report(self, chunks: List[Dict], output_path: str):
        """
        Сохраняет детальный отчёт классификации
        """
        from collections import Counter
        
        report = {
            'total_chunks': len(chunks),
            'categories': dict(Counter(c['meta'].get('category', 'unknown') for c in chunks)),
            'sentiments': dict(Counter(c['meta'].get('sentiment', 'unknown') for c in chunks)),
            'insider_count': len([c for c in chunks if c['meta'].get('is_insider', False)]),
            'top_tags': dict(Counter([tag for c in chunks for tag in c['meta'].get('tags', [])]).most_common(20))
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"📄 Отчёт классификации сохранён: {output_path}")


# Для обратной совместимости со старым кодом
def classify_chunk_mock(chunk_text: str) -> Dict:
    """Устаревшая функция, оставлена для совместимости"""
    import random
    categories = ["технологии", "бизнес", "политика", "наука", "общее"]
    return {
        'category': random.choice(categories),
        'tags': [f"tag_{i}" for i in range(3)],
        'sentiment': random.choice(["positive", "neutral", "negative"])
    }
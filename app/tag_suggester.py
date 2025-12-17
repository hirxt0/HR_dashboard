"""
tag_suggester.py - Модуль для предложения и исправления тегов
"""
import difflib
from typing import List, Tuple, Dict, Any
from database import get_all_tags

def normalize_text(text: str) -> str:
    """Нормализация текста для сравнения"""
    if not text:
        return ""
    
    text = text.lower()
    text = text.replace('ё', 'е')
    text = ''.join(c for c in text if c.isalnum() or c.isspace())
    text = ' '.join(text.split())
    
    return text

def calculate_similarity(text1: str, text2: str) -> float:
    """Вычисление схожести двух строк"""
    if not text1 or not text2:
        return 0.0
    
    norm1 = normalize_text(text1)
    norm2 = normalize_text(text2)
    
    if norm1 in norm2 or norm2 in norm1:
        return 0.9
    
    return difflib.SequenceMatcher(None, norm1, norm2).ratio()

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
        
        try:
            all_tags_list = get_all_tags()
            
            # Собираем частоту тегов
            for tag in all_tags_list:
                self.tag_counts[tag] = self.tag_counts.get(tag, 0) + 1
            
            # Убираем дубликаты и сортируем по частоте
            unique_tags = list(set(all_tags_list))
            self.all_tags = sorted(unique_tags, key=lambda x: self.tag_counts.get(x, 0), reverse=True)
            
            self._initialized = True
            print(f"Загружено {len(self.all_tags)} уникальных тегов")
            
        except Exception as e:
            print(f"Ошибка инициализации TagSuggester: {e}")
    
    def get_suggestions(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Получение предложений для запроса"""
        if not query or len(query) < 2:
            return []

        if not self._initialized:
            self.initialize()

        query_normalized = normalize_text(query)
        suggestions = []

        for tag in self.all_tags:
            if len(tag) < 3:
                continue
            
            similarity = calculate_similarity(query, tag)
            is_exact = normalize_text(tag) == query_normalized

            contains_query = query_normalized in normalize_text(tag)
            query_contains_tag = normalize_text(tag) in query_normalized

            if is_exact:
                min_similarity = 0.0
                similarity = 1.0
            elif contains_query or query_contains_tag:
                min_similarity = 0.3
                similarity = min(0.9, similarity * 1.2)
            else:
                min_similarity = 0.6

            if similarity >= min_similarity:
                suggestions.append({
                    'tag': tag,
                    'similarity': similarity,
                    'is_exact': is_exact,
                    'count': self.tag_counts.get(tag, 0)
                })

        # Сортируем по приоритету
        suggestions.sort(key=lambda x: (
            -x['is_exact'],
            -x['similarity'],
            -x['count']
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
    
    def get_all_unique_tags(self) -> List[str]:
        """Получить все уникальные теги"""
        if not self._initialized:
            self.initialize()
        return self.all_tags
    
    def get_tag_count(self) -> int:
        """Получить количество уникальных тегов"""
        if not self._initialized:
            self.initialize()
        return len(self.all_tags)
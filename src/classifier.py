import sqlite3
import json
from typing import List, Dict, Optional, Tuple
import requests
from dataclasses import dataclass
import time
import re
from dotenv import load_dotenv
import os

load_dotenv()
API_KEY = os.getenv("API_KEY")

@dataclass
class ChunkData:
    """Структура данных чанка"""
    chunk_id: int
    text: str
    existing_metadata: Dict

class LLMMetadataClassifier:
    """
    LLM генерирует теги, взял бесплатную LLama-3.3
    """
    
    def __init__(self, db_path: str = "telegram_data.db", api_key: Optional[str] = None):
        """
        Args:
            db_path: путь к SQLite базе
            api_key: API ключ для Groq (бесплатный - 30 req/min)
        """
        self.db_path = db_path
        self.api_key = api_key
        self.api_url = "https://api.groq.com/openai/v1/chat/completions"
        self.model = "llama-3.3-70b-versatile"
        
        self._init_db()
        
    def _init_db(self):
        """коннект с бд и создание новых колонок"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            columns_to_add = [
                ("llm_tags", "TEXT"),
                ("sentiment", "TEXT"),
                ("sentiment_score", "REAL"),
            ]
            
            for col_name, col_type in columns_to_add:
                try:
                    cursor.execute(f"""
                        ALTER TABLE chunks ADD COLUMN {col_name} {col_type}
                    """)
                except sqlite3.OperationalError:
                    pass
            
            conn.commit()
    
    def get_chunks(self, limit: Optional[int] = None) -> List[ChunkData]:
        """получаем из бд чанки, должно быть название у колонки - chunks"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            query = "SELECT id, text, metadata FROM chunks"
            if limit:
                query += f" LIMIT {limit}"
            
            cursor.execute(query)
            rows = cursor.fetchall()
            
            chunks = []
            for row in rows:
                chunk_id, text, metadata_str = row
                
                try:
                    existing_metadata = json.loads(metadata_str) if metadata_str else {}
                except:
                    existing_metadata = {}
                
                chunks.append(ChunkData(
                    chunk_id=chunk_id,
                    text=text,
                    existing_metadata=existing_metadata
                ))
            return chunks
    
    def analyze_with_llm(self, text: str) -> Tuple[List[str], str, float]:
        """
        анализ текста на теги и настроение
        
        вывод:
            ([теги], настроение, уверенность в настроении)
        """
        prompt = f"""Проанализируй следующий текст и выполни два задания:

1. ТЕГИ: Выдели ровно 5 самых важных тегов на русском языке
   - Ключевые темы и концепции
   - 1-2 слова максимум
   - Конкретные и информативные

2. НАСТРОЕНИЕ: Определи эмоциональную окраску текста
   - positive (позитивный, оптимистичный)
   - neutral (нейтральный, фактический)
   - negative (негативный, критический)
   - Уверенность от 0.0 до 1.0

Текст:
{text[:1500]}

Формат ответа (строго соблюдай):
ТЕГИ: тег1, тег2, тег3, тег4, тег5
НАСТРОЕНИЕ: positive|neutral|negative
УВЕРЕННОСТЬ: 0.85

Пример:
ТЕГИ: технологии, искусственный интеллект, стартапы, инвестиции, инновации
НАСТРОЕНИЕ: positive
УВЕРЕННОСТЬ: 0.92"""

        try:
            response = requests.post(
                self.api_url,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                },
                json={
                    "model": self.model,
                    "messages": [
                        {
                            "role": "system",
                            "content": "Ты эксперт по анализу текстов. Строго следуй формату ответа."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": 0.3,
                    "max_tokens": 150,
                    "stream": False
                },
                timeout=30
            )
            
            # проверка статус ответа
            if response.status_code != 200:
                print(f" API ошибка: HTTP {response.status_code}")
                print(f"   Ответ: {response.text[:200]}")
                return [], 'neutral', 0.0
            
            # парсим JSON
            result = response.json()
            
            if 'error' in result:
                print(f" API ошибка: {result['error'].get('message', 'Unknown error')}")
                return [], 'neutral', 0.0
            
            # извлекаем ответ LLM
            if result.get('choices') and len(result['choices']) > 0:
                content = result['choices'][0]['message']['content'].strip()
                
                # парсим ответ
                tags = self._parse_tags(content)
                sentiment, confidence = self._parse_sentiment(content)
                
                return tags, sentiment, confidence
            else:
                return [], 'neutral', 0.0
                
        except Exception as e:
            print(f"Ошибка LLM анализа: {e}")
            return [], 'neutral', 0.0
    
    def _parse_tags(self, content: str) -> List[str]:
        """парсинг тегов из ответа LLM"""
        # поиск строки с тегами
        tags_match = re.search(r'ТЕГИ:\s*(.+?)(?:\n|$)', content, re.IGNORECASE)
        if tags_match:
            tags_text = tags_match.group(1).strip()
            tags = [tag.strip() for tag in tags_text.split(',')]
            tags = [tag for tag in tags if tag and len(tag) > 2][:5]
            return tags
        return []
    
    def _parse_sentiment(self, content: str) -> Tuple[str, float]:
        """парсинг настроения из ответа LLM"""

        sentiment = 'neutral'
        sentiment_match = re.search(r'НАСТРОЕНИЕ:\s*(positive|neutral|negative)', content, re.IGNORECASE)
        if sentiment_match:
            sentiment = sentiment_match.group(1).lower()
        
        confidence = None
        conf_match = re.search(r'УВЕРЕННОСТЬ:\s*(0?\.\d+|1\.0)', content, re.IGNORECASE)
        if conf_match:
            try:
                confidence = float(conf_match.group(1))
            except:
                confidence = 0.5
        
        return sentiment, confidence
    
    
    def save_to_db(self, chunk_id: int, llm_tags: List[str], 
                   sentiment: str, sentiment_score: float):
        """Сохранение результатов в БД"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE chunks 
                SET llm_tags = ?, 
                    sentiment = ?,
                    sentiment_score = ?
                WHERE id = ?
            """, (
                json.dumps(llm_tags, ensure_ascii=False),
                sentiment,
                sentiment_score,
                chunk_id
            ))
            
            conn.commit()
    
    def process_chunk(self, chunk: ChunkData, delay: float = 0.5) -> Dict:
        """
        обработка одного чанка
        """
        print(f"Текст: {chunk.text[:100]}")
        
        # анализируем
        llm_tags, sentiment, sentiment_score = self.analyze_with_llm(chunk.text)
    
        
        print(f" LLM теги: {', '.join(llm_tags)}")
        print(f" Настроение: {sentiment} (уверенность: {sentiment_score:.2f})")
        
        
        # сохраняем в БД
        self.save_to_db(
            chunk.chunk_id, llm_tags, sentiment, sentiment_score)
        
        # задержка для rate limit
        time.sleep(delay)
        
        return {
            'chunk_id': chunk.chunk_id,
            'llm_tags': llm_tags,
            'sentiment': sentiment,
            'sentiment_score': sentiment_score,
        }
    
    def process_all(self, limit: Optional[int] = None, delay: float = 0.5):
        """
        Обработка всех чанков из БД
        """

        chunks = self.get_chunks(limit=limit)
        
        if not chunks:
            print("Нет чанков для обработки")
            return
        
        results = []
       
        for i, chunk in enumerate(chunks, 1):
            
            try:
                result = self.process_chunk(chunk, delay=delay)
                results.append(result)
                
                    
            except Exception as e:
                print(f" Ошибка обработки chunk {chunk.chunk_id}: {e}")
                continue
        
        return results


def main():
    """
    Пример использования
    """
    # инициализация
    classifier = LLMMetadataClassifier(
        db_path="название БД",
        api_key=API_KEY
    )
    
    # обработка
    results = classifier.process_all(
        limit=10,
        delay=0.5 
    )
    

if __name__ == "__main__":
    main()

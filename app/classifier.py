# classifier.py
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
API_KEY = os.getenv("GROQ_API_KEY")

@dataclass
class ChunkData:
    """Структура данных чанка"""
    chunk_id: int
    text: str
    existing_metadata: Dict

class LLMMetadataClassifier:
    """
    LLM генерирует теги из заданного списка с объяснением
    """
    
    # Список доступных тегов для выбора
    PREDEFINED_TAGS = [
        # Технологии
        "технологии", "искусственный интеллект", "программирование", "кибербезопасность", "данные",
        "робототехника", "автоматизация", "облачные вычисления", "big data", "машинное обучение",
        
        # Бизнес
        "бизнес", "стартапы", "инвестиции", "маркетинг", "финансы", "экономика",
        "предпринимательство", "управление", "стратегия", "конкуренция", "рынок",
        
        # Образование
        "образование", "обучение", "исследования", "наука", "университет",
        "курсы", "навыки", "развитие", "знания", "академия",
        
        # Разное
        "новости", "аналитика", "тренды", "инновации", "развитие", "будущее",
        "здоровье", "экология", "политика", "культура", "спорт", "путешествия",
        "медицина", "работа", "карьера", "лидерство", "команда", "продуктивность",
        "социальные сети", "медиа", "искусство", "музыка", "кино", "литература"
    ]
    
    def __init__(self, db_path: str = "telegram_data.db", api_key: Optional[str] = None):
        """
        Args:
            db_path: путь к SQLite базе
            api_key: API ключ для Groq
        """
        self.db_path = db_path
        self.api_key = api_key
        self.api_url = "https://api.groq.com/openai/v1/chat/completions"
        self.model = "llama-3.3-70b-versatile"
        
        if db_path and os.path.exists(db_path):
            self._init_db()
        
    def _init_db(self):
        """коннект с бд и создание новых колонок"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Проверяем существование таблицы chunks
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='chunks'
            """)
            
            if cursor.fetchone():
                columns_to_add = [
                    ("llm_tags", "TEXT"),
                    ("sentiment", "TEXT"),
                    ("explanation", "TEXT"),  # Вместо sentiment_score
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
        """получаем из бд чанки"""
        if not os.path.exists(self.db_path):
            return []
            
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Проверяем существование таблицы
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='chunks'
            """)
            
            if not cursor.fetchone():
                return []
            
            query = "SELECT id, text, metadata FROM chunks WHERE llm_tags IS NULL"
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
    # Добавьте эту функцию в класс LLMMetadataClassifier в classifier.py

    def generate_recommendations(self, tag: str, signal_type: str, 
                                sentiment_distribution: Dict[str, float],
                                mentions_count: int, trend: str) -> List[str]:
        """
        Генерация рекомендаций для сигнала с помощью LLM

        Args:
            tag: тег сигнала
            signal_type: тип сигнала (problem, opportunity, early_trend и т.д.)
            sentiment_distribution: распределение настроений
            mentions_count: количество упоминаний
            trend: тренд (up, down, stable)

        Returns:
            Список рекомендаций (2-4 рекомендации)
        """
        if not self.api_key or self.api_key == "ваш_ключ_здесь":
            print("Ошибка: API ключ не настроен для генерации рекомендаций")
            return ["Проанализировать ситуацию по тегу", "Установить мониторинг"]

        # Определяем контекст в зависимости от типа сигнала
        signal_context = {
            'problem': "негативная ситуация, требующая решения",
            'growing_problem': "нарастающая негативная проблема",
            'new_problem': "новая негативная проблема",
            'opportunity': "позитивная возможность для развития", 
            'growing_opportunity': "растущая позитивная возможность",
            'new_opportunity': "новая позитивная возможность",
            'new_trend': "новый тренд на рынке",
            'emerging_trend': "зарождающийся тренд",
            'early_trend': "формирующийся тренд"
        }

        context = signal_context.get(signal_type, "тренд на рынке")

        # Формируем промпт для LLM
        prompt = f"""Ты HR-аналитик в крупной компании. Проанализируй следующий сигнал и дай конкретные рекомендации:

    ТЕГ СИГНАЛА: "{tag}"
    ТИП СИГНАЛА: {signal_type} ({context})
    РАСПРЕДЕЛЕНИЕ НАСТРОЕНИЙ:
     - Позитивных: {sentiment_distribution.get('positive', 0)}%
     - Негативных: {sentiment_distribution.get('negative', 0)}%
     - Нейтральных: {sentiment_distribution.get('neutral', 0)}%
    ВСЕГО УПОМИНАНИЙ: {mentions_count}
    ТРЕНД: {'растет' if trend == 'up' else 'падает' if trend == 'down' else 'стабилен'}

    СФЕРА АНАЛИЗА:
    1. HR и кадровая политика (рекрутинг, обучение, мотивация)
    2. Технологии и инновации
    3. Бизнес-стратегия
    4. Маркетинг и коммуникации
    5. Управление рисками

    СФОРМИРУЙ 3-4 КОНКРЕТНЫХ РЕКОМЕНДАЦИИ ДЛЯ КОМПАНИИ.
    Каждая рекомендация должна быть:
    - Практической и выполнимой
    - Конкретной (что именно делать)
    - Ориентированной на результат
    - Уместной для типа сигнала
    - Максимально краткой (1 предложение)

    Формат ответа (СТРОГО соблюдай):
    РЕКОМЕНДАЦИЯ 1: [текст рекомендации]
    РЕКОМЕНДАЦИЯ 2: [текст рекомендации] 
    РЕКОМЕНДАЦИЯ 3: [текст рекомендации]
    РЕКОМЕНДАЦИЯ 4: [текст рекомендации]

    Пример для негативного сигнала:
    РЕКОМЕНДАЦИЯ 1: Провести анализ источников негатива по теме "{tag}"
    РЕКОМЕНДАЦИЯ 2: Разработать план коммуникации для улучшения восприятия
    РЕКОМЕНДАЦИЯ 3: Организовать встречу с ключевыми стейкхолдерами
    РЕКОМЕНДАЦИЯ 4: Установить мониторинг упоминаний темы в течение месяца"""

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
                            "content": """Ты опытный HR-аналитик и бизнес-консультант. 
                            Давай конкретные, практические рекомендации для бизнеса.
                            Строго следуй формату ответа. Каждая рекомендация - одно предложение.
                            Рекомендации должны быть разными и охватывать разные аспекты."""
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": 0.4,
                    "max_tokens": 300,
                    "stream": False
                },
                timeout=20
            )

            if response.status_code != 200:
                print(f"❌ API ошибка при генерации рекомендаций: HTTP {response.status_code}")
                return self._get_default_recommendations(tag, signal_type)

            result = response.json()

            if 'error' in result:
                print(f"❌ API ошибка: {result['error'].get('message', 'Unknown error')}")
                return self._get_default_recommendations(tag, signal_type)

            if result.get('choices') and len(result['choices']) > 0:
                content = result['choices'][0]['message']['content'].strip()
                print(f"🤖 LLM сгенерировал рекомендации для тега '{tag}':")
                print(content)

                # Парсим рекомендации
                recommendations = self._parse_recommendations(content)

                # Если рекомендаций мало, добавляем дефолтные
                if len(recommendations) < 2:
                    recommendations.extend(self._get_default_recommendations(tag, signal_type)[:2])

                # Уникальные рекомендации
                unique_recommendations = []
                for rec in recommendations:
                    if rec and rec not in unique_recommendations and len(rec) > 10:
                        unique_recommendations.append(rec)

                return unique_recommendations[:4]  # Максимум 4 рекомендации

            else:
                return self._get_default_recommendations(tag, signal_type)

        except Exception as e:
            print(f"❌ Ошибка генерации рекомендаций: {e}")
            return self._get_default_recommendations(tag, signal_type)

    def _parse_recommendations(self, content: str) -> List[str]:
        """Парсинг рекомендаций из ответа LLM"""
        recommendations = []

        # Ищем все рекомендации в формате "РЕКОМЕНДАЦИЯ X: текст"
        pattern = r'РЕКОМЕНДАЦИЯ\s*\d+\s*:\s*(.+?)(?:\n|$|РЕКОМЕНДАЦИЯ)'
        matches = re.findall(pattern, content, re.IGNORECASE | re.DOTALL)

        for match in matches:
            rec = match.strip()
            # Очищаем от лишних символов
            rec = re.sub(r'^\W+|\W+$', '', rec)
            if rec and len(rec) > 10:  # Минимальная длина
                recommendations.append(rec)

        # Если не нашли в формате, ищем списком
        if not recommendations:
            lines = content.split('\n')
            for line in lines:
                line = line.strip()
                # Пропускаем пустые строки и заголовки
                if (line and 
                    not line.startswith('РЕКОМЕНДАЦИЯ') and
                    not line.startswith('ТЕГ') and
                    not line.startswith('ТИП') and
                    len(line) > 10):
                    # Убираем маркеры списка
                    line = re.sub(r'^[•\-\d\.\)]\s*', '', line)
                    recommendations.append(line)

        return recommendations

    def _get_default_recommendations(self, tag: str, signal_type: str) -> List[str]:
        """Резервные рекомендации если LLM не сработал"""
        default_recommendations = {
            'problem': [
                f"Провести анализ причин негатива по теме '{tag}'",
                f"Разработать план коммуникации по теме '{tag}'",
                f"Организовать встречу с ключевыми стейкхолдерами",
                f"Установить регулярный мониторинг упоминаний темы"
            ],
            'growing_problem': [
                f"СРОЧНО проанализировать ситуацию по теме '{tag}'",
                f"Разработать кризисный план коммуникации",
                f"Создать рабочую группу для решения проблемы",
                f"Установить ежедневный мониторинг ситуации"
            ],
            'opportunity': [
                f"Проанализировать потенциал темы '{tag}' для бизнеса",
                f"Разработать стратегию использования возможностей",
                f"Изучить успешные кейсы по теме '{tag}'",
                f"Рассмотреть инвестиции в данное направление"
            ],
            'growing_opportunity': [
                f"Активно использовать позитивный тренд по теме '{tag}'",
                f"Рассмотреть возможность инвестиций в направление",
                f"Разработать маркетинговую кампанию",
                f"Изучить возможность партнерства в этой сфере"
            ],
            'new_trend': [
                f"Установить мониторинг нового тренда '{tag}'",
                f"Изучить ранние признаки тренда",
                f"Проанализировать потенциал для бизнеса",
                f"Разработать стратегию реагирования"
            ]
        }

        # Ищем наиболее подходящие рекомендации
        if signal_type in default_recommendations:
            return default_recommendations[signal_type]
        elif 'problem' in signal_type:
            return default_recommendations['problem']
        elif 'opportunity' in signal_type:
            return default_recommendations['opportunity']
        else:
            return [
                f"Проанализировать тренд '{tag}'",
                f"Установить мониторинг темы",
                f"Разработать план действий",
                f"Оценить влияние на бизнес"
            ]
    def analyze_with_llm(self, text: str) -> Tuple[List[str], str, str]:
            """
            анализ текста на теги (выбирает из заданного списка) и настроение
            с кратким объяснением выбора тегов

            вывод:
                ([теги], настроение, объяснение)
            """
            if not self.api_key or self.api_key == "ваш_ключ_здесь":
                print("Ошибка: API ключ не настроен")
                return [], 'neutral', 'API ключ не настроен'

            if not text or len(text.strip()) < 10:
                print("Текст слишком короткий для анализа")
                return [], 'neutral', 'Текст слишком короткий'

            # Формируем строку с доступными тегами
            tags_list_str = "\n".join([f"- {tag}" for tag in self.PREDEFINED_TAGS])

            prompt = f"""Проанализируй следующий текст и выполни три задания:

    1. ТЕГИ: Выбери ровно 3-5 самых подходящих тегов из предоставленного списка.
       - Выбирай теги, которые лучше всего описывают содержание текста
       - Только теги из списка ниже, не придумывай новые
       - Теги должны быть разнообразными и охватывать разные аспекты текста

    2. НАСТРОЕНИЕ: Определи как можно охарктеризовать этот текст для компании СберБанк
       - positive (позитивный, оптимистичный)
       - neutral (нейтральный, фактический) 
       - negative (негативный, критический)

    3. ОБЪЯСНЕНИЕ: Кратко объясни почему выбраны именно эти теги (1-2 предложения)
       - Объясни связь между текстом и выбранными тегами
       - Максимально кратко, по делу

    Доступные теги:
    {tags_list_str}

    Текст для анализа:
    {text[:1500]}

    Формат ответа (строго соблюдай, это очень важно!):
    ТЕГИ: тег1, тег2, тег3, тег4, тег5
    НАСТРОЕНИЕ: positive|neutral|negative
    ОБЪЯСНЕНИЕ: Краткое объяснение почему выбраны именно эти теги

    Пример:
    ТЕГИ: технологии, искусственный интеллект, инновации
    НАСТРОЕНИЕ: positive
    ОБЪЯСНЕНИЕ: В тексте обсуждаются последние достижения в области ИИ и их применение в различных отраслях, что напрямую связано с технологиями и инновациями."""

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
                                "content": """Ты эксперт по анализу текстов. 
                                ВАЖНО: Строго следуй формату ответа.
                                Выбирай теги ТОЛЬКО из предоставленного списка.
                                Объяснение должно быть кратким (1-2 предложения)."""
                            },
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        "temperature": 0.3,
                        "max_tokens": 250,  # Увеличил для объяснения
                        "stream": False
                    },
                    timeout=30
                )

                # проверка статуса ответа
                if response.status_code != 200:
                    print(f" API ошибка: HTTP {response.status_code}")
                    print(f"   Ответ: {response.text[:200]}")
                    return [], 'neutral', f'API ошибка: {response.status_code}'

                # парсим JSON
                result = response.json()

                if 'error' in result:
                    print(f" API ошибка: {result['error'].get('message', 'Unknown error')}")
                    return [], 'neutral', f"API ошибка: {result['error'].get('message', 'Unknown error')}"

                # извлекаем ответ LLM
                if result.get('choices') and len(result['choices']) > 0:
                    content = result['choices'][0]['message']['content'].strip()
                    print(f"Ответ LLM:\n{content}\n{'-'*50}")

                    # парсим ответ
                    tags = self._parse_tags(content)
                    sentiment = self._parse_sentiment(content)
                    explanation = self._parse_explanation(content)

                    return tags, sentiment, explanation
                else:
                    return [], 'neutral', 'Не удалось получить ответ от LLM'

            except requests.exceptions.Timeout:
                print("Таймаут при запросе к API")
                return [], 'neutral', 'Таймаут при запросе к API'
            except Exception as e:
                print(f"Ошибка LLM анализа: {e}")
                return [], 'neutral', f'Ошибка анализа: {str(e)[:100]}'

    def _parse_tags(self, content: str) -> List[str]:
        """парсинг тегов из ответа LLM"""
        tags_match = re.search(r'ТЕГИ:\s*(.+?)(?:\n|$)', content, re.IGNORECASE)
        if tags_match:
            tags_text = tags_match.group(1).strip()
            tags = [tag.strip() for tag in tags_text.split(',')]
            
            # Фильтруем только теги из списка
            valid_tags = []
            for tag in tags:
                # Проверяем точное совпадение
                if tag in self.PREDEFINED_TAGS and tag not in valid_tags:
                    valid_tags.append(tag)
                else:
                    # Проверяем совпадение без учета регистра
                    for predefined_tag in self.PREDEFINED_TAGS:
                        if predefined_tag.lower() == tag.lower() and predefined_tag not in valid_tags:
                            valid_tags.append(predefined_tag)
                            break
            
            # Если тегов мало, пытаемся найти альтернативы
            if len(valid_tags) < 2 and len(tags) > 0:
                # Пробуем найти теги по ключевым словам
                tag_lower = tags[0].lower()
                for predefined_tag in self.PREDEFINED_TAGS:
                    if tag_lower in predefined_tag.lower() and predefined_tag not in valid_tags:
                        valid_tags.append(predefined_tag)
                        if len(valid_tags) >= 3:
                            break
            
            return valid_tags[:5]  # Возвращаем максимум 5 тегов
        
        return []
    
    def _parse_sentiment(self, content: str) -> str:
        """парсинг настроения из ответа LLM"""
        sentiment = 'neutral'
        sentiment_match = re.search(r'НАСТРОЕНИЕ:\s*(positive|neutral|negative)', content, re.IGNORECASE)
        if sentiment_match:
            sentiment = sentiment_match.group(1).lower()
        
        return sentiment
    
    def _parse_explanation(self, content: str) -> str:
        """парсинг объяснения из ответа LLM"""
        explanation = 'Объяснение не предоставлено'
        
        # Ищем объяснение после метки ОБЪЯСНЕНИЕ:
        explanation_match = re.search(r'ОБЪЯСНЕНИЕ:\s*(.+?)(?:\n\n|\n$|$)', content, re.IGNORECASE | re.DOTALL)
        if explanation_match:
            explanation = explanation_match.group(1).strip()
            # Ограничиваем длину
            if len(explanation) > 500:
                explanation = explanation[:497] + "..."
        else:
            # Попробуем найти объяснение без метки
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if 'ТЕГИ:' in line and i + 3 < len(lines):
                    # Возможно, объяснение через 2-3 строки после тегов
                    for j in range(1, 4):
                        if i + j < len(lines):
                            potential_explanation = lines[i + j].strip()
                            if (potential_explanation and 
                                not potential_explanation.startswith('НАСТРОЕНИЕ:') and
                                not potential_explanation.startswith('ТЕГИ:') and
                                not potential_explanation.startswith('УВЕРЕННОСТЬ:')):
                                explanation = potential_explanation
                                break
        
        return explanation
    
    def save_to_db(self, chunk_id: int, llm_tags: List[str], 
                   sentiment: str, explanation: str):
        """Сохранение результатов в БД"""
        if not os.path.exists(self.db_path):
            print(f"БД {self.db_path} не найдена, сохранение пропущено")
            return
            
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE chunks 
                SET llm_tags = ?, 
                    sentiment = ?,
                    explanation = ?
                WHERE id = ?
            """, (
                json.dumps(llm_tags, ensure_ascii=False),
                sentiment,
                explanation,
                chunk_id
            ))
            
            conn.commit()
    
    def process_chunk(self, chunk: ChunkData, delay: float = 0.5) -> Dict:
        """
        обработка одного чанка
        """
        print(f"\n{'='*60}")
        print(f"📋 Обработка чанка #{chunk.chunk_id}")
        print(f"{'='*60}")
        print(f"📝 Текст (первые 200 символов):")
        print(f"   {chunk.text[:200]}...")
        
        # анализируем
        llm_tags, sentiment, explanation = self.analyze_with_llm(chunk.text)
        
        print(f"\n✅ Результаты анализа:")
        print(f"   🏷️  Теги: {', '.join(llm_tags) if llm_tags else 'не выбраны'}")
        print(f"   😊 Настроение: {sentiment}")
        print(f"   📝 Объяснение: {explanation}")
        
        # сохраняем в БД
        self.save_to_db(
            chunk.chunk_id, llm_tags, sentiment, explanation)
        
        print(f"💾 Сохранено в БД")
        
        # задержка для rate limit
        time.sleep(delay)
        
        return {
            'chunk_id': chunk.chunk_id,
            'llm_tags': llm_tags,
            'sentiment': sentiment,
            'explanation': explanation,
        }
    
    def process_all(self, limit: Optional[int] = None, delay: float = 0.5):
        """
        Обработка всех чанков из БД
        """
        chunks = self.get_chunks(limit=limit)
        
        if not chunks:
            print("ℹ️  Нет чанков для обработки")
            return []
        
        print(f"🔍 Найдено {len(chunks)} чанков для обработки")
        
        results = []
        for i, chunk in enumerate(chunks, 1):
            print(f"\n🔄 Обработка {i}/{len(chunks)}")
            
            try:
                result = self.process_chunk(chunk, delay=delay)
                results.append(result)
                
            except Exception as e:
                print(f"❌ Ошибка обработки chunk {chunk.chunk_id}: {e}")
                continue
        
        print(f"\n{'='*60}")
        print(f"🎉 Обработка завершена! Обработано: {len(results)} чанков")
        
        # Статистика
        if results:
            sentiments = [r['sentiment'] for r in results]
            from collections import Counter
            sentiment_stats = Counter(sentiments)
            
            print(f"\n📊 Статистика настроений:")
            for sentiment, count in sentiment_stats.items():
                print(f"   {sentiment}: {count}")
        
        return results

    def analyze_text(self, text: str) -> Dict:
        """
        Анализ текста без использования БД
        """
        print(f"\n{'='*60}")
        print(f"🔍 Анализ текста")
        print(f"{'='*60}")
        print(f"📝 Текст (первые 200 символов):")
        print(f"   {text[:200]}...")
        
        llm_tags, sentiment, explanation = self.analyze_with_llm(text)
        
        result = {
            'llm_tags': llm_tags,
            'sentiment': sentiment,
            'explanation': explanation,
        }
        
        print(f"\n✅ Результат анализа:")
        print(f"   🏷️  Теги: {', '.join(llm_tags)}")
        print(f"   😊 Настроение: {sentiment}")
        print(f"   📝 Объяснение: {explanation}")
        
        return result


def main():
    """
    Пример использования
    """
    # инициализация
    classifier = LLMMetadataClassifier(
        db_path="telegram_data.db",
        api_key=API_KEY
    )
    
    if API_KEY is None:
        print("❌ Ошибка: GROQ_API_KEY не найден в переменных окружения")
        print("📝 Создайте файл .env с содержимым: GROQ_API_KEY=ваш_ключ")
        return
    
    # обработка
    results = classifier.process_all(
        limit=5,
        delay=0.5 
    )
    
    # Вывод результатов
    if results:
        print(f"\n📋 Итоговые результаты:")
        for result in results:
            print(f"\nЧанк {result['chunk_id']}:")
            print(f"  🏷️  {', '.join(result['llm_tags'])}")
            print(f"  😊 {result['sentiment']}")
            print(f"  📝 {result['explanation']}")


if __name__ == "__main__":
    main()
# пока только набросок 


from sentence_transformers import SentenceTransformer
from keybert import KeyBERT
from transformers import pipeline
import numpy as np
import re
from typing import List, Dict

class MetadataProcessorRU:
    """
    Обработка метаданных для текстов на русском
    """
    
    def __init__(self, embedding_model_name='intfloat/multilingual-e5-large'):

        print(f"Загрузка модели эмбеддингов: {embedding_model_name}")
        self.embedding_model = SentenceTransformer(embedding_model_name)
        self.kw_model = KeyBERT(model=self.embedding_model)
        
        try:
            self.sentiment_model = pipeline(
                'sentiment-analysis',
                model='blanchefort/rubert-base-cased-sentiment',
                device=0 if self._has_cuda() else -1
            )
            print("Sentiment модель: blanchefort/rubert-base-cased-sentiment\n")
        except Exception as e:
            print(f"Ошибка - {e}")
            self.sentiment_model = pipeline(
                'sentiment-analysis',
                model='cardiffnlp/twitter-xlm-roberta-base-sentiment',
                device=-1
            )
        
        self.insider_patterns = [
            #паттерны
            r'эксклюзивно',
            r'источники сообщают',
            r'как стало известно',
            r'инсайдеры утверждают',
            r'по неофициальной информации',
            r'от анонимного источника',
            r'конфиденциальные данные',
            r'утечка информации',
            r'эксклюзив',
            r'по данным источников',
            r'как узнал(а|и)?',
            r'стало известно из источников',
            r'неофициально',
            r'инсайд'
        ]
    
    def _has_cuda(self):
        """Проверка доступности GPU"""
        import torch
        return torch.cuda.is_available()
    
    def extract_tags(self, text: str, top_n: int = 5) -> List[str]:
        """
        Извлекает ключевые слова из РУССКОГО текста
        """
        try:
            keywords = self.kw_model.extract_keywords(
                text,
                keyphrase_ngram_range=(1, 2),
                stop_words='russian',
                top_n=top_n,
                use_maxsum=True,
                nr_candidates=20
            )
            return [kw[0] for kw in keywords]
        except Exception as e:
            print(f"Ошибка извлечения тегов: {e}")
            return []
    
    def analyze_sentiment(self, text: str) -> Dict:
        """
        Анализирует настроение РУССКОГО текста
        """
        try:
            truncated_text = text[:512]
            result = self.sentiment_model(truncated_text)[0]
            
            label = result['label'].lower()
            
            # Маппинг для русской модели
            sentiment_map = {
                'positive': 'positive',
                'neutral': 'neutral', 
                'negative': 'negative'
            }
            
            sentiment = sentiment_map.get(label, 'neutral')
            
            return {
                'sentiment': sentiment,
                'score': float(result['score'])
            }
        except Exception as e:
            print(f"Ошибка анализа sentiment: {e}")
            return {'sentiment': 'neutral', 'score': 0.0}
    
    def detect_insider(self, text: str) -> Dict:
        """
        Определяет инсайдерскую информацию
        """
        text_lower = text.lower()
        matches = 0
        matched_patterns_list = []
        
        for pattern in self.insider_patterns:
            if re.search(pattern, text_lower):
                matches += 1
                matched_patterns_list.append(pattern)
        
        is_insider = matches >= 2
        confidence = min(matches * 0.25, 1.0)
        
        return {
            'is_insider': is_insider,
            'confidence': float(confidence),
            'matched_patterns': matches
        }
    
    def classify_topic(self, text: str, tags: List[str] = None) -> Dict:
        """
        Классификация темы для РУССКИХ новостей с подробным анализом
        Возвращает основную тему и детальный анализ по всем темам
        """
        if tags is None:
            tags = []
            
        text_lower = text.lower()
        tags_lower = ' '.join(tags).lower()
        combined = text_lower + ' ' + tags_lower
        
        # РУССКИЕ категории и ключевые слова с весами
        topic_keywords = {
            'технологии': [
                "искусственный интеллект",
                "ИИ", "ai", "ai-инфраструктура",
                "облачные технологии", "облако", "cloud",
                "чипы", "полупроводники", "микросхемы",
                "автоматизация", "автоматизированные системы", 
                "регулирование ии", "законы об ии", 
                "венчур", "ar", "vr", "mr",
                "метавиртуальная реальность", "умный дом",
                "iot", "квантовые технологии", "квантовые компьютеры", 
                "cybersecurity", "киберугрозы", "уязвимости", 
                "цифровая трансформация", "стартапы", "технологических", "софт", 
                "программа", "алгоритм", "данные", "обработа"
            ],
            'бизнес': [
                'компани', 'бизнес', 'рынок', 'выручк', 'прибыл',
                'инвестиц', 'акци', 'сделк', 'капитал', 'фонд',
                'предприним', 'корпорац', 'холдинг', 'слияни',
                'поглощени', 'переговор', 'контракт', 'партнерств'
            ],
            'политика': [
                'правительств', 'выбор', 'политик', 'закон',
                'президент', 'дума', 'министр', 'депутат', 'власт',
                'партия', 'оппозиц', 'парламент', 'государств', 'федеральн',
                'местн', 'административн', 'санкци', 'соглащени'
            ],
            'наука': [
                'исследовани', 'учён', 'научн', 'открыти',
                'эксперимент', 'лаборатори', 'университет', 'академи',
                'публикаци', 'научным', 'теори', 'гипотез'
            ],
            'здоровье': [
                'здоровь', 'медицин', 'болезн', 'больниц',
                'врач', 'лечени', 'вакцин', 'пациент', 'клиник',
                'фармацевтическ', 'препарат', 'диагност', 'эпидеми'
            ],
            'спорт': [
                'игра', 'команда', 'игрок', 'чемпионат',
                'лига', 'матч', 'турнир', 'спорт', 'футбол', 'хоккей',
                'атлет', 'соревнован', 'тренер', 'олимпиад'
            ],
            'экономика': [
                'экономик', 'инфляци', 'цен', 'тариф', 'курс',
                'доллар', 'рубл', 'банк', 'кредит', 'ввп', 'бюджет',
                'налог', 'таможен', 'экспорт', 'импорт'
            ],
            'финансы': [
                'финанс', 'инвестор', 'трейд', 'биржа', 'торг',
                'валют', 'крипто', 'bitcoin', 'ethereum', 'ценн', 'облигаци',
                'портфел', 'доходность', 'риск'
            ],
            'недвижимость': [
                'квартир', 'дом', 'недвижимост', 'арендн', 'ипотек',
                'строител', 'земел', 'участок', 'цен на жиль'
            ]
        }
        
        # Подсчет по каждой теме
        topic_scores = {}
        for topic, keywords in topic_keywords.items():
            matches = []
            for kw in keywords:
                # Считаем вхождение ключевого слова в текст
                count = combined.count(kw)
                if count > 0:
                    matches.append({'keyword': kw, 'count': count})
            
            # Общий счет для темы
            score = sum(m['count'] for m in matches)
            topic_scores[topic] = {
                'score': score,
                'matches': matches,
                'keyword_count': len(matches)
            }
        
        # Получение основной темы и фильтрование
        topic_scores_filtered = {k: v for k, v in topic_scores.items() if v['score'] > 0}
        
        if topic_scores_filtered:
            main_topic = max(topic_scores_filtered, key=lambda x: topic_scores_filtered[x]['score'])
        else:
            main_topic = 'общее'
        
        return {
            'main_topic': main_topic,
            'scores': {k: v['score'] for k, v in topic_scores.items()},
            'details': topic_scores_filtered
        }
    
    def get_topic_summary(self, topic_analysis: Dict) -> str:
        """
        Возвращает текстовое резюме анализа темы
        """
        main_topic = topic_analysis['main_topic']
        scores = topic_analysis['scores']
        
        sorted_topics = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
        if sorted_topics[0][1] == 0:
            return "тема не определена (нет совпадений)"
        
        summary_parts = []
        for topic, score in sorted_topics[:3]:
            if score > 0:
                summary_parts.append(f"{topic} ({score})")
        
        return ", ".join(summary_parts) if summary_parts else "общее"
    
    def process_chunk(self, chunk_id: str, text: str) -> Dict:
        """
        Полная обработка одного чанка
        """
        tags = self.extract_tags(text)
        sentiment_data = self.analyze_sentiment(text)
        topic_analysis = self.classify_topic(text, tags)
        insider_data = self.detect_insider(text)
        
        return {
            'chunk_id': chunk_id,
            'metadata': {
                'tags': tags,
                'sentiment': sentiment_data['sentiment'],
                'sentiment_score': sentiment_data['score'],
                'topic': topic_analysis['main_topic'],
                'topic_scores': topic_analysis['scores'],
                'topic_details': topic_analysis['details'],
                'is_insider': insider_data['is_insider'],
                'insider_confidence': insider_data['confidence']
            }
        }
    
    def process_batch(self, chunks: List[Dict], batch_size: int = 50) -> List[Dict]:
        """
        Батчевая обработка с оптимизацией
        """
        results = []
        total = len(chunks)
        
        print(f"Обработка {total} чанков...\n")
        
        for i in range(0, total, batch_size):
            batch = chunks[i:i + batch_size]
            
            for chunk in batch:
                try:
                    result = self.process_chunk(
                        chunk_id=chunk.get('chunk_id', f'chunk_{i}'),
                        text=chunk['text']
                    )
                    results.append(result)
                except Exception as e:
                    print(f"Ошибка: {e}")
                    continue
            
            processed = len(results)
            print(f"Обработано {processed}/{total} чанков ({processed/total*100:.1f}%)")
        
        print(f"\n {len(results)}/{total} чанков успешно обработаны")
        return results



if __name__ == "__main__":
    import json
    
    processor = MetadataProcessorRU(
        embedding_model_name='intfloat/multilingual-e5-large'
    )
    
    test_chunks = [
        {
            'chunk_id': 'test_001',
            'text': """
            Роботы GITAI самостоятельно и собрали 5-метровую конструкцию - фундамент будущих внеземных модулей.
            Это пример того, как связка ИИ + робототехника начинает давать тот самый технологический скачок, 
            на который долго рассчитывали: автономные системы, способные строить инфраструктуру без участия человека, 
            открывают путь к базам на Луне, Марсе и орбите.
            """
        },
        {
            'chunk_id': 'test_002',
            'text': """
            Как стало известно из источников, близких к руководству компании,
            готовятся массовые увольнения в IT-отделе. По неофициальной информации,
            под сокращение попадут до 200 сотрудников. Инсайдеры утверждают, что
            решение связано с падением прибыли в последнем квартале.
            """
        },
        {
            'chunk_id': 'test_003',
            'text': """
            Центробанк повысил ключевую ставку до 16%. Эксперты прогнозируют
            дальнейший рост инфляции. Курс доллара достиг 95 рублей.
            """
        }
    ]
    
    results = processor.process_batch(test_chunks)   
    for result in results:
        print(f"ID: {result['chunk_id']}")
        print(f"Теги: {', '.join(result['metadata']['tags']) if result['metadata']['tags'] else 'нет'}")
        print(f"Настроение: {result['metadata']['sentiment']} "
              f"({result['metadata']['sentiment_score']:.2%})")
        print(f"Основная тема: {result['metadata']['topic']}")
        
        # Показываем рейтинг всех тем
        print(f"Рейтинг по темам:")
        scores = sorted(result['metadata']['topic_scores'].items(), 
                       key=lambda x: x[1], reverse=True)
        for topic, score in scores:
            if score > 0:
                print(f"      • {topic}: {score}")
        
        main_topic = result['metadata']['topic']
        if main_topic in result['metadata']['topic_details']:
            details = result['metadata']['topic_details'][main_topic]
            print(f"Найденные слова ({main_topic}):")
            for match in details['matches'][:5]:  
                print(f"      • '{match['keyword']}': встречается {match['count']} раз(а)")
        
        print(f"Инсайд: {result['metadata']['is_insider']} "
              f"(уверенность: {result['metadata']['insider_confidence']:.2%})")
        print()
    
    # Сохранение
    with open('chunks_metadata_ru.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print("✅ Результаты сохранены в chunks_metadata_ru.json")
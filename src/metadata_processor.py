# пока только набросок 


from transformers import pipeline
import re
from typing import List, Dict
from collections import Counter
import numpy as np

# Для KeyBERT
try:
    from keybert import KeyBERT
    KEYBERT_AVAILABLE = True
except ImportError:
    KEYBERT_AVAILABLE = False
    print("⚠️ KeyBERT не установлен. Установите: pip install keybert")

# Для YAKE
try:
    import yake
    YAKE_AVAILABLE = True
except ImportError:
    YAKE_AVAILABLE = False
    print("⚠️ YAKE не установлен. Установите: pip install yake")


class MetadataProcessorRU:
    """
    Обработка метаданных для текстов на русском с улучшенной экстракцией тегов
    """
    
    def __init__(self, tag_extraction_method: str = 'keybert'):
        """
        Args:
            tag_extraction_method: 'keybert', 'yake', или 'frequency'
        """
        print(f"🤖 Инициализация MetadataProcessorRU...")
        print(f"   Метод экстракции тегов: {tag_extraction_method}")
        
        self.tag_method = tag_extraction_method
        
        # Sentiment модель
        try:
            self.sentiment_model = pipeline(
                'sentiment-analysis',
                model='blanchefort/rubert-base-cased-sentiment',
                device=-1  # CPU
            )
            print("   ✓ Sentiment: blanchefort/rubert-base-cased-sentiment")
        except Exception as e:
            print(f"   ⚠️ Sentiment ошибка: {e}")
            self.sentiment_model = None
        
        # KeyBERT модель
        self.keybert_model = None
        if tag_extraction_method == 'keybert' and KEYBERT_AVAILABLE:
            try:
                # Используем легкую многоязычную модель
                self.keybert_model = KeyBERT(model='paraphrase-multilingual-MiniLM-L12-v2')
                print("   ✓ KeyBERT: paraphrase-multilingual-MiniLM-L12-v2")
            except Exception as e:
                print(f"   ⚠️ KeyBERT ошибка: {e}, используем fallback")
                self.tag_method = 'yake'
        
        # YAKE экстрактор
        self.yake_extractor = None
        if tag_extraction_method == 'yake' and YAKE_AVAILABLE:
            try:
                # Параметры для русского языка
                self.yake_extractor = yake.KeywordExtractor(
                    lan="ru",
                    n=2,  # максимальная длина n-грамм
                    dedupLim=0.7,
                    dedupFunc='seqm',
                    windowsSize=1,
                    top=10
                )
                print("   ✓ YAKE: русский экстрактор")
            except Exception as e:
                print(f"   ⚠️ YAKE ошибка: {e}")
        
        # Стоп-слова для очистки
        self.stopwords = {
            'и','в','во','не','что','он','на','я','с','со','как','а','то','все',
            'она','так','его','но','да','ты','к','у','за','от','из','по','для',
            'о','об','же','или','если','когда','бы','ее','они','мы','мой','твой',
            'ее','их','быть','это','также','всё','того','есть','был','была','были',
            'будет','может','очень','уже','только','более','можно','такой','такая','год',
            'говорит','сказал','стал','стала','стали','будут','были'
        }
        
        # Паттерны инсайдов
        self.insider_patterns = [
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
        
        print("✅ Инициализация завершена\n")
    
    def extract_tags(self, text: str, top_n: int = 5) -> List[str]:
        """
        Извлекает ключевые слова из текста
        """
        if not text or len(text) < 20:
            return []
        
        try:
            # KeyBERT - наилучшее качество
            if self.tag_method == 'keybert' and self.keybert_model:
                return self._extract_tags_keybert(text, top_n)
            
            # YAKE - быстрый и хороший
            elif self.tag_method == 'yake' and self.yake_extractor:
                return self._extract_tags_yake(text, top_n)
            
            # Fallback - частотный анализ
            else:
                return self._extract_tags_frequency(text, top_n)
                
        except Exception as e:
            print(f"⚠️ Ошибка экстракции тегов: {e}")
            return self._extract_tags_frequency(text, top_n)
    
    def _extract_tags_keybert(self, text: str, top_n: int) -> List[str]:
        """Экстракция через KeyBERT"""
        keywords = self.keybert_model.extract_keywords(
            text,
            keyphrase_ngram_range=(1, 2),  # 1-2 словные фразы
            stop_words=list(self.stopwords),
            top_n=top_n * 2,  # Берем больше для фильтрации
            diversity=0.7  # Разнообразие результатов
        )
        
        # Фильтруем и форматируем
        tags = []
        for keyword, score in keywords:
            # Очищаем от лишнего
            keyword = keyword.lower().strip()
            
            # Пропускаем короткие и числа
            if len(keyword) < 3 or keyword.isdigit():
                continue
            
            # Пропускаем если только стоп-слова
            words = keyword.split()
            if all(w in self.stopwords for w in words):
                continue
            
            tags.append(keyword)
            
            if len(tags) >= top_n:
                break
        
        return tags
    
    def _extract_tags_yake(self, text: str, top_n: int) -> List[str]:
        """Экстракция через YAKE"""
        keywords = self.yake_extractor.extract_keywords(text)
        
        tags = []
        for keyword, score in keywords:
            keyword = keyword.lower().strip()
            
            # Фильтрация
            if len(keyword) < 3:
                continue
            
            words = keyword.split()
            if all(w in self.stopwords for w in words):
                continue
            
            tags.append(keyword)
            
            if len(tags) >= top_n:
                break
        
        return tags
    
    def _extract_tags_frequency(self, text: str, top_n: int) -> List[str]:
        """Fallback: частотный анализ с улучшениями"""
        # Нормализация
        text_norm = re.sub(r"[^а-яёa-z0-9\s]", " ", text.lower())
        
        # Извлекаем биграммы и триграммы тоже
        words = text_norm.split()
        
        # Униграммы
        unigrams = [w for w in words if len(w) >= 4 and w not in self.stopwords]
        
        # Биграммы
        bigrams = []
        for i in range(len(words) - 1):
            if words[i] not in self.stopwords or words[i+1] not in self.stopwords:
                bigram = f"{words[i]} {words[i+1]}"
                if len(bigram) >= 6:
                    bigrams.append(bigram)
        
        # Считаем частоты
        all_grams = unigrams + bigrams
        counts = Counter(all_grams)
        
        # Фильтруем частые, но бессмысленные
        meaningful = []
        for gram, count in counts.most_common(top_n * 2):
            # Пропускаем если встречается только 1 раз
            if count < 2 and len(all_grams) > 10:
                continue
            
            meaningful.append(gram)
            
            if len(meaningful) >= top_n:
                break
        
        return meaningful
    
    def analyze_sentiment(self, text: str) -> Dict:
        """Анализ тональности"""
        if not self.sentiment_model:
            return {'sentiment': 'neutral', 'score': 0.0}
        
        try:
            truncated = text[:512]
            result = self.sentiment_model(truncated)[0]
            
            label = result['label'].lower()
            sentiment_map = {
                'positive': 'positive',
                'neutral': 'neutral',
                'negative': 'negative'
            }
            
            return {
                'sentiment': sentiment_map.get(label, 'neutral'),
                'score': float(result['score'])
            }
        except Exception as e:
            print(f"⚠️ Ошибка sentiment: {e}")
            return {'sentiment': 'neutral', 'score': 0.0}
    
    def detect_insider(self, text: str) -> Dict:
        """Детекция инсайдерской информации"""
        text_lower = text.lower()
        matches = 0
        matched_patterns = []
        
        for pattern in self.insider_patterns:
            if re.search(pattern, text_lower):
                matches += 1
                matched_patterns.append(pattern)
        
        is_insider = matches >= 2
        confidence = min(matches * 0.25, 1.0)
        
        return {
            'is_insider': is_insider,
            'confidence': float(confidence),
            'matched_patterns': matches
        }
    
    def classify_topic(self, text: str, tags: List[str] = None) -> Dict:
        """Классификация темы с улучшенными ключевыми словами"""
        if tags is None:
            tags = []
        
        text_lower = text.lower()
        tags_lower = ' '.join(tags).lower()
        combined = text_lower + ' ' + tags_lower
        
        # Расширенные категории с весами
        topic_keywords = {
            'технологии': {
                'keywords': [
                    ('искусственный интеллект', 3), ('нейросети', 3), ('машинное обучение', 3),
                    ('ИИ', 2), ('ai', 2), ('ml', 2), ('deep learning', 3),
                    ('облачные технологии', 2), ('облако', 1), ('cloud', 2),
                    ('чипы', 2), ('полупроводники', 2), ('gpu', 2), ('nvidia', 2),
                    ('автоматизация', 2), ('роботы', 2), ('робототехника', 2),
                    ('квантовые компьютеры', 3), ('блокчейн', 2), ('криптография', 2),
                    ('большие данные', 2), ('big data', 2), ('аналитика данных', 2),
                    ('программирование', 2), ('разработка', 1), ('софт', 1),
                    ('стартап', 1), ('технологий', 1), ('цифров', 1)
                ]
            },
            'бизнес': {
                'keywords': [
                    ('компани', 1), ('бизнес', 2), ('рынок', 2), ('выручк', 2),
                    ('прибыл', 2), ('инвестиц', 2), ('акци', 2), ('сделк', 2),
                    ('капитал', 2), ('фонд', 2), ('стартап', 2), ('венчур', 2),
                    ('unicorn', 3), ('единорог', 3), ('ipo', 2), ('слияни', 2),
                    ('поглощени', 2), ('партнерств', 2), ('корпорац', 2)
                ]
            },
            'наука': {
                'keywords': [
                    ('исследовани', 2), ('учён', 2), ('научн', 2), ('открыти', 3),
                    ('эксперимент', 2), ('лаборатори', 2), ('университет', 2),
                    ('публикаци', 2), ('статья', 1), ('peer-review', 2),
                    ('докторант', 2), ('диссертаци', 2), ('академии', 2)
                ]
            },
            'образование': {
                'keywords': [
                    ('курс', 2), ('обучени', 2), ('образовани', 2), ('студент', 2),
                    ('преподаватель', 2), ('лекци', 2), ('семинар', 2), ('вебинар', 2),
                    ('онлайн-курс', 2), ('сертификат', 2), ('университет', 1),
                    ('школа', 1), ('буткемп', 2), ('bootcamp', 2)
                ]
            },
            'политика': {
                'keywords': [
                    ('правительств', 2), ('закон', 2), ('законопроект', 2),
                    ('президент', 2), ('дума', 2), ('министр', 2), ('депутат', 2),
                    ('власт', 2), ('партия', 2), ('выбор', 2), ('санкци', 2),
                    ('регулирование', 2), ('госуслуги', 2)
                ]
            },
            'экономика': {
                'keywords': [
                    ('экономик', 2), ('инфляци', 2), ('цен', 1), ('тариф', 2),
                    ('курс', 1), ('доллар', 2), ('рубл', 2), ('банк', 2),
                    ('кредит', 2), ('ввп', 2), ('бюджет', 2), ('налог', 2),
                    ('центробанк', 2), ('цб', 2), ('ключевая ставка', 3)
                ]
            },
            'медиа': {
                'keywords': [
                    ('контент', 2), ('блогер', 2), ('стрим', 2), ('youtube', 2),
                    ('подкаст', 2), ('социальные сети', 2), ('инфлюенсер', 2),
                    ('медиа', 2), ('сми', 2), ('новост', 1), ('репортаж', 2)
                ]
            },
            'криптовалюты': {
                'keywords': [
                    ('bitcoin', 3), ('биткоин', 3), ('ethereum', 3), ('эфир', 2),
                    ('криптовалют', 2), ('блокчейн', 2), ('nft', 2), ('токен', 2),
                    ('майнинг', 2), ('defi', 2), ('web3', 2), ('крипто', 2)
                ]
            }
        }
        
        # Подсчет с весами
        topic_scores = {}
        for topic, config in topic_keywords.items():
            score = 0
            matches = []
            
            for keyword, weight in config['keywords']:
                count = combined.count(keyword)
                if count > 0:
                    weighted_score = count * weight
                    score += weighted_score
                    matches.append({
                        'keyword': keyword,
                        'count': count,
                        'weight': weight,
                        'score': weighted_score
                    })
            
            topic_scores[topic] = {
                'score': score,
                'matches': matches,
                'keyword_count': len(matches)
            }
        
        # Получаем топ темы
        scored_topics = {k: v['score'] for k, v in topic_scores.items() if v['score'] > 0}
        
        if scored_topics:
            main_topic = max(scored_topics, key=scored_topics.get)
        else:
            main_topic = 'общее'
        
        return {
            'main_topic': main_topic,
            'scores': {k: v['score'] for k, v in topic_scores.items()},
            'details': {k: v for k, v in topic_scores.items() if v['score'] > 0}
        }
    
    def process_chunk(self, chunk_id: str, text: str) -> Dict:
        """Полная обработка чанка"""
        tags = self.extract_tags(text, top_n=7)  # Увеличили до 7
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


if __name__ == "__main__":
    # Тестирование разных методов
    test_text = """
    Компания OpenAI представила новую версию GPT-5, которая демонстрирует 
    значительные улучшения в понимании контекста и генерации кода. 
    Искусственный интеллект теперь способен решать более сложные задачи 
    в области машинного обучения и обработки естественного языка.
    Инвесторы уже проявили интерес к новой разработке.
    """
    
    print("="*60)
    print("ТЕСТИРОВАНИЕ ЭКСТРАКЦИИ ТЕГОВ")
    print("="*60)
    
    for method in ['keybert', 'yake', 'frequency']:
        print(f"\n🔹 Метод: {method.upper()}")
        try:
            processor = MetadataProcessorRU(tag_extraction_method=method)
            tags = processor.extract_tags(test_text, top_n=7)
            print(f"   Теги: {', '.join(tags)}")
        except Exception as e:
            print(f"   ❌ Ошибка: {e}")

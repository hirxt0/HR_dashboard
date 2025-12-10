# пока только набросок 


from transformers import pipeline
import re
from typing import List, Dict
from collections import Counter
import numpy as np
import os
import pickle
from sklearn.preprocessing import LabelEncoder
from sklearn.linear_model import LogisticRegression

class MetadataProcessorRU:
    """
    Обработка метаданных для текстов на русском
    """
    
    def __init__(self, embedding_model_name: str = None):
        
        print("Инициализация MetadataProcessorRU (эмбеддинги отключены)")
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
        self.topic_clf = None
        self.topic_le = None
    
    def _has_cuda(self):
        """Проверка доступности GPU"""
        import torch
        return torch.cuda.is_available()
    
    def extract_tags(self, text: str, top_n: int = 5) -> List[str]:
        """
        Извлекает ключевые слова из русского текста
        """
        try:
            # Простая частотная выборка слов без эмбеддингов
            # Нормализуем текст: приводим к нижнему регистру и убираем пунктуацию
            text_norm = re.sub(r"[^а-яёa-z0-9\s]", " ", text.lower())
            # Берём слова длиной >=3
            words = re.findall(r"\b[а-яёa-z]{3,}\b", text_norm)

            stopwords = {
                'и','в','во','не','что','он','на','я','с','со','как','а','то','все',
                'она','так','его','но','да','ты','к','у','за','от','из','по','для',
                'о','об','же','или','если','когда','бы','ее','они','мы','мой','твой',
                'ее','их','быть','это','также','всё','того','есть'
            }

            filtered = [w for w in words if w not in stopwords]
            counts = Counter(filtered)
            most_common = [w for w, _ in counts.most_common(top_n)]
            return most_common
        except Exception as e:
            print(f"Ошибка извлечения тегов: {e}")
            return []
    
    def analyze_sentiment(self, text: str) -> Dict:
        """
        Анализирует настроение русского текста
        """
        try:
            truncated_text = text[:512]
            result = self.sentiment_model(truncated_text)[0]
            
            label = result['label'].lower()
            
            # Маппинг
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
        Классификация темы для русских новостей с подробным анализом
        Возвращает основную тему и детальный анализ по всем темам
        """
        if tags is None:
            tags = []
            
        text_lower = text.lower()
        tags_lower = ' '.join(tags).lower()
        combined = text_lower + ' ' + tags_lower
        
        # русские категории и ключевые слова с весами
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
                'эксперимент', 'лаборатори', 'университет', 'академии',
                'публикаци', 'научным', 'теори', 'гипотез',
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
                count = combined.count(kw)
                if count > 0:
                    matches.append({'keyword': kw, 'count': count})
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

    def classify_by_vector(self, vector, topic_prototypes: Dict[str, List[float]] = None) -> Dict:
        """
        Классификация темы по вектору-эмбеддингу.

        Параметры:
        - vector: список или numpy-массив чисел (эмбеддинг для новости/чанка)
        - topic_prototypes: опционально словарь {topic: prototype_vector}

        Возвращает:
        - если переданы прототипы: основную тему и косинусные сходства ко всем прототипам
        - иначе: нормированную версию вектора и его норма
        """
        try:
            vec = np.array(vector, dtype=float)
        except Exception as e:
            return {'error': f'invalid_vector: {e}'}

        norm = np.linalg.norm(vec)
        if norm == 0 or np.isnan(norm):
            return {'error': 'zero_or_invalid_vector'}

        vec_norm = vec / norm

        if topic_prototypes:
            sims = {}
            for topic, proto in topic_prototypes.items():
                try:
                    p = np.array(proto, dtype=float)
                    pnorm = np.linalg.norm(p)
                    if pnorm == 0 or np.isnan(pnorm):
                        sims[topic] = 0.0
                    else:
                        sims[topic] = float(np.dot(vec_norm, p / pnorm))
                except Exception:
                    sims[topic] = 0.0

            # Выбираем тему с максимальным сходством
            main = max(sims, key=sims.get)
            return {
                'main_topic': main,
                'similarities': sims,
                'vector_norm': norm
            }

        # Без прототипов возвращаем нормированный вектор и его норму
        return {
            'vector_norm': float(norm),
            'vector_normalized': vec_norm.tolist()
        }

    def train_topic_classifier(self, embeddings: np.ndarray, labels: List[str], model_path: str = None, classifier: str = 'logistic', **kwargs) -> Dict:
        """
        Обучает supervised классификатор тем на эмбеддингах.

        Параметры:
        - embeddings: numpy array shape (n_samples, dim)
        - labels: list of str длины n_samples
        - model_path: если указан — сохраняет модель и label encoder в этот файл (joblib)
        - classifier: 'logistic' (по умолч для классификатора (например, C для LogisticRegression)
анию). Можно расширить.
        - kwargs: дополнительные параметры
        Возвращает словарь с информацией о модели и метриках (пока базово).
        """
        X = np.array(embeddings)
        if X.ndim != 2:
            raise ValueError('embeddings must be 2D array (n_samples, dim)')

        if len(labels) != X.shape[0]:
            raise ValueError('labels length must match number of embeddings')

        info = {}
        if classifier == 'logistic':
            le = LabelEncoder()
            y = le.fit_transform(labels)
            clf = LogisticRegression(max_iter=1000, **kwargs)
            clf.fit(X, y)
            # Сохраняем в атрибуты
            self.topic_clf = clf
            self.topic_le = le
            info = {'n_classes': len(le.classes_), 'classes': list(le.classes_)}
        else:
            # fallback: centroid classifier (no sklearn required)
            labels_arr = list(labels)
            classes = []
            class_to_idx = {}
            for lbl in labels_arr:
                if lbl not in class_to_idx:
                    class_to_idx[lbl] = len(classes)
                    classes.append(lbl)

            # compute centroids
            centroids = {}
            for cls in classes:
                idxs = [i for i, l in enumerate(labels_arr) if l == cls]
                pts = X[idxs]
                ctr = np.mean(pts, axis=0)
                # normalize centroid
                nrm = np.linalg.norm(ctr)
                if nrm == 0 or np.isnan(nrm):
                    continue
                centroids[cls] = (ctr / nrm).tolist()

            self.topic_clf = {'type': 'centroid', 'centroids': centroids}
            self.topic_le = {'classes': classes, 'map': class_to_idx}
            info = {'n_classes': len(classes), 'classes': classes, 'clf_type': 'centroid'}

        if model_path:
            dirp = os.path.dirname(model_path)
            if dirp and not os.path.exists(dirp):
                os.makedirs(dirp, exist_ok=True)
            with open(model_path, 'wb') as f:
                pickle.dump({'model': self.topic_clf, 'le': self.topic_le}, f)
            info['model_path'] = model_path

        return info

    def load_topic_classifier(self, model_path: str):
        """
        Загружает ранее сохранённый классификатор тем (joblib с {'model','le'}).
        """
        if not os.path.exists(model_path):
            raise FileNotFoundError(model_path)
        with open(model_path, 'rb') as f:
            data = pickle.load(f)
        clf = data.get('model') if isinstance(data, dict) else data
        le = data.get('le') if isinstance(data, dict) else None
        self.topic_clf = clf
        self.topic_le = le
        return {'loaded': True, 'model_path': model_path}

    def predict_topic_from_embedding(self, vector, return_proba: bool = True) -> Dict:
        """
        Предсказывает тему по одному эмбеддингу используя загруженный/обученный классификатор.

        Возвращает:
        - если есть классификатор: {'topic': str, 'score': float, 'proba': {topic:prob}}
        - иначе возвращает {'error': 'no_model'}
        """
        if self.topic_clf is None or self.topic_le is None:
            return {'error': 'no_model'}

        vec = np.array(vector, dtype=float)
        if vec.ndim == 1:
            x = vec
        elif vec.ndim == 2 and vec.shape[0] == 1:
            x = vec[0]
        else:
            # Не поддерживаем батч здесь
            return {'error': 'invalid_vector_shape'}

        # sklearn model
        try:
            if hasattr(self.topic_clf, 'predict'):
                X = x.reshape(1, -1)
                pred_idx = self.topic_clf.predict(X)[0]
                topic = self.topic_le.inverse_transform([pred_idx])[0] if hasattr(self.topic_le, 'inverse_transform') else pred_idx
                out = {'topic': topic}
                if return_proba and hasattr(self.topic_clf, 'predict_proba'):
                    probs = self.topic_clf.predict_proba(X)[0]
                    if hasattr(self.topic_le, 'inverse_transform'):
                        proba_map = {self.topic_le.inverse_transform([i])[0]: float(probs[i]) for i in range(len(probs))}
                    else:
                        proba_map = {str(i): float(probs[i]) for i in range(len(probs))}
                    out['proba'] = proba_map
                    out['score'] = max(probs.tolist())
                return out
        except Exception:
            pass

        # fallback centroid classifier
        if isinstance(self.topic_clf, dict) and self.topic_clf.get('type') == 'centroid':
            vec_norm = x / np.linalg.norm(x)
            sims = {}
            for topic, proto in self.topic_clf['centroids'].items():
                p = np.array(proto, dtype=float)
                sims[topic] = float(np.dot(vec_norm, p))
            main = max(sims, key=sims.get)
            return {'topic': main, 'similarities': sims, 'score': sims[main]}

        return {'error': 'unknown_model_type'}

    def classify_vectors_batch(self, vectors: List, topic_prototypes: Dict[str, List[float]] = None) -> List[Dict]:
        """
        Обработка батча векторов — обёртка над `classify_by_vector`.
        Возвращает список словарей с результатами для каждого вектора.
        """
        results = []
        for vec in vectors:
            results.append(self.classify_by_vector(vec, topic_prototypes))
        return results

    def build_topic_prototypes(self, topic_texts: Dict[str, List[str]], embedder, batch_size: int = 32) -> Dict[str, List[float]]:
        """
        Построение прототипов тем (усреднённые эмбеддинги) из примеров текстов.

        Параметры:
        - topic_texts: словарь {topic: [text1, text2, ...]}
        - embedder: объект с методами `split(text)` и `normalized_embeddings(chunks, batch_size)`
                   либо с методом `embedding(chunks, batch_size)` возвращающим numpy-матрицу.
                   Также допустима передача callablе, принимающего список строк и возвращающего массив.
        - batch_size: размер батча для кодирования

        Возвращает словарь {topic: prototype_vector_as_list}
        """
        prototypes = {}

        for topic, texts in (topic_texts or {}).items():
            topic_embs = []
            for text in texts:
                # Разбиваем на чанки, если есть splitter
                chunks = [text]
                if hasattr(embedder, 'split'):
                    try:
                        chunks = embedder.split(text)
                    except Exception:
                        chunks = [text]

                # Получаем эмбеддинги
                arr = None
                if hasattr(embedder, 'normalized_embeddings'):
                    try:
                        arr = embedder.normalized_embeddings(chunks, batch_size=batch_size)
                    except Exception:
                        arr = None
                if arr is None and hasattr(embedder, 'embedding'):
                    try:
                        arr = embedder.embedding(chunks, batch_size=batch_size)
                        # нормируем по L2
                        arr = arr / np.linalg.norm(arr, axis=1, keepdims=True)
                    except Exception:
                        arr = None
                if arr is None and callable(embedder):
                    try:
                        arr = np.array(embedder(chunks))
                        if arr.ndim == 1:
                            arr = arr.reshape(1, -1)
                        arr = arr / np.linalg.norm(arr, axis=1, keepdims=True)
                    except Exception:
                        arr = None

                if arr is None:
                    continue

                if arr.ndim == 1:
                    arr = arr.reshape(1, -1)

                topic_embs.append(arr)

            if not topic_embs:
                continue

            # объединяем все матрицы эмбеддингов по вертикали и усредняем
            all_embs = np.vstack(topic_embs)
            proto = np.mean(all_embs, axis=0)
            proto_norm = np.linalg.norm(proto)
            if proto_norm == 0 or np.isnan(proto_norm):
                continue
            proto = proto / proto_norm
            prototypes[topic] = proto.tolist()

        return prototypes
    
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
    
    print("Результаты сохранены в chunks_metadata_ru.json")
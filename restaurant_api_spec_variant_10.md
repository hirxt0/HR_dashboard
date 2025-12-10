# Specification: API для анализа данных ресторанов (Вариант 10)

**Дата:** 2025-12-07

Краткое описание

Вы — аналитик ресторанной индустрии. Ваша задача — разработать спецификацию API для анализа ресторанных данных и отзывов. Спецификация должна быть ясной, выполнима в течение 35–40 минут и пригодной для реализации с использованием pandas + FastAPI.

## **1. System Prompt**

```system
You are a restaurant industry analyst.

Your task is to build an API for restaurant data analysis.

Constraints:
- Analyze: ratings, reviews, cuisine types, locations
- Sentiment analysis: count positive/negative/neutral reviews
- No NLP models, use simple keyword matching
- Support cuisine and location filtering
- Rating scale 1-5 stars

Input format:
- CSV: restaurant_name, cuisine, location, rating, review_count, avg_review_rating, review_text (optional)
- Rating: 1-5 (float)
- Location: city/state

Output format:
- JSON: avg_rating, top_cuisines, location_statistics, review_sentiment_distribution
- Include restaurant count by criteria

Functions to implement:
    get_top_restaurants(cuisine, location, min_reviews)
    get_cuisine_statistics(location)
    get_review_sentiment_summary(restaurant_name)

Acceptance criteria:
    - Filtering by cuisine and location works
    - Ratings computed correctly
    - Basic sentiment analysis is correct (keyword matching)

Notes:
- Use simple deterministic rules only (no ML/NLP models)
- Handle missing/null values sensibly
```

## **2. Данные**

### Источник

**Restaurants Dataset** (Yelp / Kaggle) — датасет ресторанов и отзывов. Для учебной задачи достаточно небольшой выборки (несколько сотен записей).

### Структура

- Файл: `restaurants.csv` (один CSV)
- Столбцы: 7

### Описание полей

- `restaurant_name` — string — имя ресторана
- `cuisine` — string — тип кухни (например: Italian, Chinese, Sushi, Fast Food)
- `location` — string — город/штат (например: "San Francisco, CA")
- `rating` — float — средняя оценка 1.0–5.0
- `review_count` — int — количество отзывов
- `avg_review_rating` — float — средняя оценка по отзывам (1.0–5.0)
- `review_text` — string (optional) — текст одного отзыва; если есть несколько отзывов, допускается отдельный `reviews.csv` с колонками `restaurant_name,review_text`.

### Пример данных (первые 5 строк)

```csv
restaurant_name,cuisine,location,rating,review_count,avg_review_rating,review_text
Trattoria Roma,Italian,"San Francisco, CA",4.5,120,4.4,"Great pasta and friendly staff"
Sushi Zen,Japanese,"San Francisco, CA",4.7,200,4.6,"Fresh sushi, would recommend"
Burger Hub,Fast Food,"Oakland, CA",3.8,85,3.7,"Fries were cold, burger OK"
Casa Mexicana,Mexican,"San Jose, CA",4.2,60,4.1,"Tasty tacos, slow service"
Noodle House,Chinese,"San Francisco, CA",4.0,40,3.9,"Decent, but a bit salty"
```

> Примечание: если `review_text` отсутствует, допускается использовать поле `avg_review_rating` для простого анализа тональности.

## **3. Форматы**

Вход:
- CSV как описано выше. `rating` и `avg_review_rating` — float 1.0–5.0. `review_count` — неотрицательный int.

Выход (обобщённый JSON):
- `avg_rating`: float — средняя оценка среди отфильтрованных ресторанов
- `top_cuisines`: list of {"cuisine": str, "avg_rating": float, "count": int}
- `location_statistics`: {location: {"avg_rating": float, "restaurant_count": int}}
- `review_sentiment_distribution`: {"positive": int, "neutral": int, "negative": int}
- `restaurant_count`: int — число ресторанов в результате

## **4. Функции и примеры**

### Функция 1: `get_top_restaurants(cuisine=None, location=None, min_reviews=0)`

Назначение: вернуть отсортированный список лучших ресторанов по `rating`, с возможностью фильтрации по `cuisine` и/или `location` и отсеиванием по `min_reviews`.

Вход:
- `cuisine: str | None` — если `None`, фильтр не применяется
- `location: str | None` — если `None`, фильтр не применяется
- `min_reviews: int` — минимальное число отзывов (>=0)

Выход (JSON):

```json
{
  "criteria": {"cuisine": "Italian", "location": "San Francisco, CA", "min_reviews": 50},
  "restaurant_count": 5,
  "top_restaurants": [
    {"restaurant_name": "Trattoria Roma", "rating": 4.5, "review_count": 120},
    {"restaurant_name": "Pasta Bella", "rating": 4.4, "review_count": 90}
  ]
}
```

Примечания: сортировка по `rating` по убыванию, tie-breaker — `review_count` по убыванию. Если результатов 0 — вернуть `restaurant_count: 0` и пустой массив.

---

### Функция 2: `get_cuisine_statistics(location=None)`

Назначение: вычислить средний рейтинг и количество ресторанов по типам кухонь; при заданной `location` — ограничиться этой локацией.

Вход:
- `location: str | None`

Выход (JSON):

```json
{
  "location": "San Francisco, CA",
  "restaurant_count": 120,
  "cuisines": [
    {"cuisine": "Japanese", "avg_rating": 4.6, "count": 20},
    {"cuisine": "Italian", "avg_rating": 4.3, "count": 25}
  ],
  "avg_rating": 4.2
}
```

Примечание: `avg_rating` — средняя по всем ресторанам указанной локации (или по всему датасету, если `location` не задан).

---

### Функция 3: `get_review_sentiment_summary(restaurant_name)`

Назначение: простой подсчёт тональности отзывов для ресторана на основе ключевых слов (без ML).

Ограничения: нельзя использовать NLP/ML модели. Использовать наборы ключевых слов для позитивной/негативной/нейтральной тональности.

Правила тональности (рекомендуемые словари):
- Позитивные: ["good", "great", "excellent", "love", "delicious", "fresh", "recommend", "friendly", "amazing", "perfect"]
- Негативные: ["bad", "terrible", "awful", "worst", "cold", "slow", "rude", "disappoint", "overpriced", "dirty"]
- Нейтральные: если позитивных == негативных или ни одно из слов не найдено → `neutral`.

Простое правило: посчитать количество позитивных и негативных совпадений в каждом отзыве; если позитивных > негативных → positive; если негативных > позитивных → negative; иначе → neutral.

Выход (JSON):

```json
{
  "restaurant_name": "Burger Hub",
  "review_count_checked": 30,
  "method": "by_reviews_text",
  "sentiment": {"positive": 8, "neutral": 12, "negative": 10}
}
```

Fallback: если `review_text` отсутствует — использовать `avg_review_rating` по отзывам: 4-5 → positive, 3 → neutral, 1-2 → negative и вернуть `method: "by_avg_rating"`.

## **5. Ограничения и обработка ошибок**

- Не использовать ML/NLP модели — только детерминированное ключевое сопоставление.
- Валидировать входы: `min_reviews >= 0`, `rating` в 1.0–5.0.
- Обработка отсутствия CSV: возвращать понятную ошибку (HTTP 400/404 в API).
- Некорректные строки (например, `rating` вне диапазона) — пропускать с логированием.
- Дубликаты `restaurant_name` — поведение должно быть явным: агрегировать по `restaurant_name` (усреднять `rating`, суммировать `review_count`) или считать за разные сущности — рекомендовано агрегировать.
- Форматы `location`: рекомендована нормализация до `City, ST`.

## **6. Реализация и производительность**

- Рекомендуемые библиотеки: `pandas`, `numpy`, `fastapi`, `uvicorn`.
- Для учебного задания загрузка CSV в память приемлема (до ~100k строк).
- Целевые времена: загрузка данных ≤ 5 с, ответ API ≈ 1–2 с.

## **7. Критерии приёмки**

- ✅ Фильтрация по `cuisine` и `location` работает (точное/частичное совпадение при опции).
- ✅ Рейтинги и агрегаты рассчитаны корректно.
- ✅ Анализ тональности базовый и корректный (ключевые слова, fallback по avg_review_rating).
- ✅ Все три функции реализованы и возвращают JSON в указанном формате.
- ✅ Обработаны граничные случаи (пустые данные, отсутствующие столбцы, некорректные параметры).
- ✅ Документация содержит примеры входов/выходов.

## **8. Примеры использования**

- Топ итальянских ресторанов в `San Francisco, CA`, `min_reviews=50`:

```python
get_top_restaurants(cuisine="Italian", location="San Francisco, CA", min_reviews=50)
```

- Статистика по кухням для `San Francisco, CA`:

```python
get_cuisine_statistics(location="San Francisco, CA")
```

- Тональность отзывов для `Trattoria Roma`:

```python
get_review_sentiment_summary("Trattoria Roma")
```

## **9. Граничные случаи и рекомендации**

- Если CSV отсутствует — возвращать ошибку и инструкцию по загрузке.
- Если запрос фильтрует до 0 ресторанов — возвращать пустые списки и `avg_rating: null`.
- Рекомендовать опцию `match_mode` для фильтрации: `exact` или `contains`.
- Логировать предупреждения для некорректных строк.

## **10. Рекомендации для Student 1 (при написании спецификации)**

- Ясность: каждое требование должно быть однозначным.
- Примеры: включите входные CSV-строки и ожидаемые JSON-ответы.
- Граничные случаи: опишите обработку null/пустых данных и ошибок.
- Реальность: задача должна укладываться в 35–40 минут.

---

Файл создан: `restaurant_api_spec_variant_10.md` в корне проекта.

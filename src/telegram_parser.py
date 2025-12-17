import html
import json
from dataclasses import dataclass
from typing import Iterable, List, Optional, Dict, Any
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from html.parser import HTMLParser
import requests


CHANNEL_URLS = [
    "https://t.me/KarpovCourses",
    "https://t.me/naumenprojectruler",
    "https://t.me/scientific_opensource",
    "https://t.me/itmo_opensource",
    "https://t.me/TheDataEconomy",
    "https://t.me/machinelearning_ru",
    "https://t.me/minobrnaukiofficial",
]


@dataclass
class TelegramMessage:
    channel: str
    message_id: Optional[str]
    text: str
    datetime: Optional[str]
    permalink: Optional[str]


def _channel_slug(url: str) -> str:
    """Extract channel slug from t.me URL."""
    parsed = urlparse(url)
    slug = parsed.path.strip("/").split("/")[0]
    if not slug:
        raise ValueError(f"Cannot extract channel name from: {url}")
    return slug


def _channel_feed_url(slug: str) -> str:
    # Public preview renders without auth; embed flag makes markup stable.
    return f"https://t.me/s/{slug}?embed=1&userpic=true"


def _fetch_html(url: str, timeout: int = 15) -> str:
    headers = {"User-Agent": "Mozilla/5.0 (compatible; TelegramScraper/1.0)"}
    with urlopen(Request(url, headers=headers), timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="ignore")


class _TelegramHTMLParser(HTMLParser):
    """Tiny parser that extracts text/timestamps/links from t.me preview HTML."""

    def __init__(self) -> None:
        super().__init__()
        self.messages: List[TelegramMessage] = []
        self._current: Optional[TelegramMessage] = None
        self._in_message = False
        self._in_text = False
        self._div_depth = 0

    def handle_starttag(self, tag: str, attrs: List[tuple]) -> None:
        attrs_dict = dict(attrs)
        class_list = attrs_dict.get("class", "").split()

        if (
            not self._in_message
            and tag == "div"
            and "tgme_widget_message" in class_list
            and "js-widget_message" in class_list
        ):
            self._in_message = True
            self._div_depth = 1
            self._current = TelegramMessage(
                channel="",
                message_id=attrs_dict.get("data-post"),
                text="",
                datetime=None,
                permalink=None,
            )
            return

        if self._in_message and tag == "div":
            self._div_depth += 1

        if self._in_message and tag == "div" and "tgme_widget_message_text" in class_list:
            self._in_text = True

        if self._in_message and tag == "time":
            if attrs_dict.get("datetime"):
                self._current.datetime = attrs_dict["datetime"]

        if self._in_message and tag == "a":
            if "tgme_widget_message_date" in class_list and attrs_dict.get("href"):
                self._current.permalink = attrs_dict["href"]

    def handle_endtag(self, tag: str) -> None:
        if self._in_text and tag == "div":
            self._in_text = False

        if self._in_message and tag == "div":
            self._div_depth -= 1
            if self._div_depth == 0:
                if self._current:
                    self.messages.append(self._current)
                self._current = None
                self._in_message = False

    def handle_data(self, data: str) -> None:
        if self._in_message and self._in_text and self._current is not None:
            text = html.unescape(data)
            self._current.text += text


def parse_messages_from_html(html_content: str, channel: str) -> List[TelegramMessage]:
    parser = _TelegramHTMLParser()
    parser.feed(html_content)
    for msg in parser.messages:
        msg.channel = channel
        msg.text = msg.text.strip()
    parser.close()
    return [m for m in parser.messages if m.text]


def fetch_channel_messages(channel_url: str, limit: int = 100) -> List[TelegramMessage]:
    slug = _channel_slug(channel_url)
    html_content = _fetch_html(_channel_feed_url(slug))
    messages = parse_messages_from_html(html_content, channel=slug)
    return messages[-limit:] if limit else messages


def fetch_all_channels(
    channel_urls: Iterable[str] = CHANNEL_URLS, limit_per_channel: int = 100
) -> List[TelegramMessage]:
    collected: List[TelegramMessage] = []
    for url in channel_urls:
        try:
            collected.extend(fetch_channel_messages(url, limit=limit_per_channel))
        except Exception as exc:  # pragma: no cover - network failures are possible
            # Swallow per-channel errors so other feeds still work.
            print(f"Failed to fetch {url}: {exc}")
    return collected


class GigaChatFilter:
    """Фильтрация контента через GigaChat API"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://gigachat.devices.sberbank.ru/api/v1"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # Промпт для классификации
        self.classification_prompt = """Ты AI-ассистент для HR-аналитика в Сбере. Проанализируй текст новости и определи:

1. РЕЛЕВАНТНОСТЬ (RELEVANT/IRRELEVANT):
   - RELEVANT: если касается ИИ, ML, Data Science, образования, науки, технологий, бизнеса, экономики, HR, новых законов, управления проектами
   - IRRELEVANT: реклама, шутки, мемы, личные истории, спам, не по теме

2. КАТЕГОРИЯ (выбери одну):
   - AI_ML_DS: Искусственный интеллект, машинное обучение, Data Science
   - EDUCATION_SCIENCE: Образование, наука, исследования, университеты
   - BUSINESS_ECONOMY: Бизнес, экономика, управление, стартапы
   - TECHNOLOGY: Технологии, IT, разработка, open source
   - REGULATION_LAW: Законы, регуляторика, политика в образовании/науке
   - PROJECT_MANAGEMENT: Управление проектами, менеджмент
   - OTHER: Другое (если релевантно, но не подходит под категории выше)
   - IRRELEVANT: Не релевантно

3. ВАЖНОСТЬ (CRITICAL/HIGH/MEDIUM/LOW):
   - CRITICAL: новые законы, регуляторные изменения, кризисные ситуации, прорывные технологии
   - HIGH: значимые исследования, изменения в образовании, важные бизнес-новости
   - MEDIUM: тренды, обзоры, аналитика, новые методики
   - LOW: информационные сообщения, анонсы, новости без существенного влияния

4. ТОНАЛЬНОСТЬ (POSITIVE/NEUTRAL/NEGATIVE):
   - POSITIVE: позитивные новости, успехи, достижения
   - NEUTRAL: нейтральное изложение фактов
   - NEGATIVE: проблемы, критика, негативные события

5. КРАТКОЕ ОБОСНОВАНИЕ на русском языке (1-2 предложения)

ТЕКСТ ДЛЯ АНАЛИЗА:
{text}

ИСТОЧНИК: {source}

Верни ответ ТОЛЬКО в JSON формате без каких-либо пояснений:
{{
  "relevance": "RELEVANT/IRRELEVANT",
  "category": "категория",
  "importance": "важность",
  "tonality": "тональность",
  "justification": "обоснование на русском"
}}"""
    
    def classify(self, text: str, source: str) -> Optional[Dict[str, Any]]:
        """Классифицирует текст и возвращает метаданные или None при ошибке."""
        try:
            prompt = self.classification_prompt.format(text=text, source=source)
            
            payload = {
                "model": "GigaChat",
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.1,
                "max_tokens": 500
            }
            
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            # Извлекаем JSON из ответа (может быть обернут в markdown код)
            content = content.strip()
            if content.startswith("```"):
                # Убираем markdown код блоки
                lines = content.split("\n")
                content = "\n".join(lines[1:-1]) if len(lines) > 2 else content
            elif content.startswith("```json"):
                lines = content.split("\n")
                content = "\n".join(lines[1:-1]) if len(lines) > 2 else content
            
            metadata = json.loads(content)
            return metadata
            
        except Exception as e:
            print(f"Ошибка классификации через GigaChat: {e}")
            return None
    
    def is_relevant(self, text: str, source: str) -> bool:
        """Проверяет релевантность текста. Возвращает True если RELEVANT."""
        metadata = self.classify(text, source)
        if metadata:
            return metadata.get("relevance", "IRRELEVANT") == "RELEVANT"
        return False  # При ошибке считаем нерелевантным
    
    def classify_and_filter(self, text: str, source: str) -> Optional[Dict[str, Any]]:
        """
        Классифицирует текст и возвращает метаданные только если релевантно.
        Возвращает None если нерелевантно или при ошибке.
        """
        metadata = self.classify(text, source)
        if metadata and metadata.get("relevance", "IRRELEVANT") == "RELEVANT":
            return metadata
        return None


def messages_as_chunks(
    messages: Iterable[TelegramMessage], 
    filter_instance: Optional[GigaChatFilter] = None
) -> List[Dict[str, str]]:
    """
    Преобразует сообщения в формат chunks (text + metadata JSON).
    Фильтрует нерелевантные сообщения если передан filter_instance.
    
    Returns:
        List[Dict[str, str]]: Список словарей с ключами 'text' и 'metadata'
    """
    chunks = []
    
    for msg in messages:
        # Фильтрация через GigaChat если передан фильтр
        if filter_instance:
            # Классифицируем и фильтруем за один вызов
            classification = filter_instance.classify_and_filter(msg.text, msg.channel)
            if not classification:
                continue  # Пропускаем нерелевантные сообщения
        else:
            classification = None
        
        # Формируем метаданные
        metadata = {
            "channel": msg.channel,
            "message_id": msg.message_id,
            "datetime": msg.datetime,
            "permalink": msg.permalink,
        }
        
        # Добавляем классификацию если есть
        if classification:
            metadata.update(classification)
        
        chunks.append({
            "text": msg.text,
            "metadata": json.dumps(metadata, ensure_ascii=False)
        })
    
    return chunks


def messages_as_dicts(messages: Iterable[TelegramMessage]) -> List[dict]:
    """Convert message objects to plain dicts for easy serialization."""
    return [
        {
            "channel": m.channel,
            "message_id": m.message_id,
            "text": m.text,
            "datetime": m.datetime,
            "permalink": m.permalink,
        }
        for m in messages
    ]


if __name__ == "__main__":
    import os
    
    # Получаем сообщения
    messages = fetch_all_channels(limit_per_channel=20)
    print(f"Получено {len(messages)} сообщений из всех каналов")
    
    # Если есть API ключ GigaChat, используем фильтрацию
    api_key = os.getenv("GIGACHAT_API_KEY")
    filter_instance = None
    if api_key:
        print("Используется фильтрация через GigaChat...")
        filter_instance = GigaChatFilter(api_key)
        chunks = messages_as_chunks(messages, filter_instance=filter_instance)
        print(f"После фильтрации осталось {len(chunks)} релевантных сообщений")
    else:
        print("GIGACHAT_API_KEY не установлен, фильтрация отключена")
        chunks = messages_as_chunks(messages, filter_instance=None)
    
    # Выводим результат в формате chunks
    print("\n" + "="*80)
    print("РЕЗУЛЬТАТ В ФОРМАТЕ CHUNKS:")
    print("="*80 + "\n")
    
    for i, chunk in enumerate(chunks, 1):
        print(f"--- Chunk {i} ---")
        print(f"TEXT: {chunk['text'][:200]}..." if len(chunk['text']) > 200 else f"TEXT: {chunk['text']}")
        print(f"METADATA: {chunk['metadata']}")
        print()


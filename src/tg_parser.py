import html
from dataclasses import dataclass
from typing import Iterable, List, Optional
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from html.parser import HTMLParser
import emoji
import re


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


def clean_telegram_text(text: str, remove_mentions_hashtags: bool = True) -> str:
    """
    Очищает текст Telegram-сообщения.
    
    Args:
        text: Исходный текст сообщения.
        remove_mentions_hashtags: Удалять ли упоминания (@) и хештеги (#).
    
    Returns:
        Очищенный текст.
    """
    if not text:
        return ""
    
    # 1. Удаляем эмодзи (два надежных способа)
    # Способ 1: Через библиотеку emoji (рекомендуется, так как она актуальнее)
    try:
        text = emoji.replace_emoji(text, replace='')
    except:
        # Способ 2: Через регулярное выражение (на случай, если библиотека не установлена)
        emoji_pattern = re.compile("["
            u"\U0001F600-\U0001F64F"  # emoticons
            u"\U0001F300-\U0001F5FF"  # symbols & pictographs
            u"\U0001F680-\U0001F6FF"  # transport & map symbols
            u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
            u"\U00002702-\U000027B0"
            u"\U000024C2-\U0001F251"
            "]+", flags=re.UNICODE)
        text = emoji_pattern.sub(r'', text)
    
    # 2. Удаляем URL-ссылки (http, https, t.me)
    url_pattern = re.compile(r'https?://\S+|t\.me/\S+')
    text = url_pattern.sub('', text)
    
    # 3. Опционально: удаляем упоминания и хештеги
    if remove_mentions_hashtags:
        mention_hashtag_pattern = re.compile(r'[@#]\w+')
        text = mention_hashtag_pattern.sub('', text)
    
    # 4. Удаляем распространенные рекламные слова (список можно расширить)
    ad_phrases = [
        r'подписывайся', r'канал', r'ссылка\s*в\s*описании', 
        r'реклама', r'промокод', r'партнер', r'бесплатно',
        r'скачать', r'зарегистрируйся', r'подписка'
    ]
    for phrase in ad_phrases:
        text = re.sub(phrase, '', text, flags=re.IGNORECASE)
    
    # 5. Удаляем лишние пробелы и переносы строк
    text = re.sub(r'\s+', ' ', text)  # Множественные пробелы -> один
    text = text.strip()
    
    return text


if __name__ == "__main__":
    messages = fetch_all_channels(limit_per_channel=20)
    dicts = messages_as_dicts(messages)
    for entry in dicts:
        preview = (entry["text"][:120] + "...") if len(entry["text"]) > 120 else entry["text"]
        preview = clean_telegram_text(preview)
        print(f"[{entry['channel']}] {entry['datetime']} {entry['permalink'] or ''} :: {preview}")


import sqlite3
import hashlib
import json
from datetime import datetime
from typing import List, Dict, Optional
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from html.parser import HTMLParser
import html
import emoji
import re
import time


# Конфигурация каналов по категориям
CHANNEL_CONFIG = {
    'технологии': [
        "https://t.me/machinelearning_ru",
        "https://t.me/itmo_opensource",
        "https://t.me/scientific_opensource",
    ],
    'образование': [
        "https://t.me/KarpovCourses",
        "https://t.me/naumenprojectruler",
    ],
    'бизнес': [
        "https://t.me/TheDataEconomy",
    ],
    'официальное': [
        "https://t.me/minobrnaukiofficial",
    ]
}


class TelegramDatabase:
    """Управление базой данных для Telegram сообщений"""
    
    def __init__(self, db_path: str = "telegram_data.db"):
        self.db_path = db_path
        self.conn = None
        self.init_database()
    
    def init_database(self):
        """Инициализация БД с правильной схемой"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        cursor = self.conn.cursor()
        
        # Таблица сообщений
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id TEXT,
                channel TEXT NOT NULL,
                channel_category TEXT,
                text TEXT NOT NULL,
                text_cleaned TEXT,
                text_hash TEXT UNIQUE,
                datetime TEXT,
                permalink TEXT,
                word_count INTEGER,
                char_count INTEGER,
                has_links BOOLEAN,
                has_mentions BOOLEAN,
                has_hashtags BOOLEAN,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица метаданных (для классификатора)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS message_metadata (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id INTEGER,
                tags TEXT,
                sentiment TEXT,
                sentiment_score REAL,
                category TEXT,
                topic_scores TEXT,
                is_insider BOOLEAN,
                insider_confidence REAL,
                processed_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (message_id) REFERENCES messages(id)
            )
        ''')
        
        # Индексы для быстрого поиска
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_text_hash ON messages(text_hash)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_channel ON messages(channel)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_datetime ON messages(datetime)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_category ON message_metadata(category)')
        
        self.conn.commit()
        print(f"✅ База данных инициализирована: {self.db_path}")
    
    def text_hash(self, text: str) -> str:
        """Создание хеша текста для дедупликации"""
        # Нормализуем текст: убираем пробелы, приводим к нижнему регистру
        normalized = re.sub(r'\s+', ' ', text.lower().strip())
        return hashlib.md5(normalized.encode()).hexdigest()
    
    def message_exists(self, text: str) -> bool:
        """Проверка существования сообщения"""
        text_hash = self.text_hash(text)
        cursor = self.conn.cursor()
        cursor.execute('SELECT 1 FROM messages WHERE text_hash = ? LIMIT 1', (text_hash,))
        return cursor.fetchone() is not None
    
    def insert_message(self, message: Dict) -> Optional[int]:
        """Вставка нового сообщения"""
        text_hash = self.text_hash(message['text'])
        
        # Проверка дубликата
        if self.message_exists(message['text']):
            return None
        
        cursor = self.conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO messages (
                    message_id, channel, channel_category, text, text_cleaned,
                    text_hash, datetime, permalink, word_count, char_count,
                    has_links, has_mentions, has_hashtags
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                message.get('message_id'),
                message['channel'],
                message.get('channel_category'),
                message['text'],
                message.get('text_cleaned', message['text']),
                text_hash,
                message.get('datetime'),
                message.get('permalink'),
                message.get('word_count', 0),
                message.get('char_count', 0),
                message.get('has_links', False),
                message.get('has_mentions', False),
                message.get('has_hashtags', False)
            ))
            
            self.conn.commit()
            return cursor.lastrowid
            
        except sqlite3.IntegrityError:
            # Дубликат по text_hash
            return None
    
    def get_unprocessed_messages(self, limit: int = None) -> List[Dict]:
        """Получить необработанные сообщения (без метаданных)"""
        cursor = self.conn.cursor()
        
        query = '''
            SELECT m.* FROM messages m
            LEFT JOIN message_metadata mm ON m.id = mm.message_id
            WHERE mm.id IS NULL
            ORDER BY m.created_at DESC
        '''
        
        if limit:
            query += f' LIMIT {limit}'
        
        cursor.execute(query)
        return [dict(row) for row in cursor.fetchall()]
    
    def insert_metadata(self, message_id: int, metadata: Dict) -> int:
        """Вставка метаданных для сообщения"""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            INSERT INTO message_metadata (
                message_id, tags, sentiment, sentiment_score,
                category, topic_scores, is_insider, insider_confidence
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            message_id,
            json.dumps(metadata.get('tags', []), ensure_ascii=False),
            metadata.get('sentiment'),
            metadata.get('sentiment_score'),
            metadata.get('category'),
            json.dumps(metadata.get('topic_scores', {}), ensure_ascii=False),
            metadata.get('is_insider', False),
            metadata.get('insider_confidence', 0.0)
        ))
        
        self.conn.commit()
        return cursor.lastrowid
    
    def search_by_tags(self, tags: List[str], limit: int = 10) -> List[Dict]:
        """Поиск сообщений по тегам"""
        cursor = self.conn.cursor()
        
        # Создаём условия поиска для каждого тега
        conditions = ' OR '.join(['mm.tags LIKE ?' for _ in tags])
        params = [f'%{tag}%' for tag in tags]
        params.append(limit)
        
        query = f'''
            SELECT m.*, mm.*
            FROM messages m
            JOIN message_metadata mm ON m.id = mm.message_id
            WHERE {conditions}
            ORDER BY m.datetime DESC
            LIMIT ?
        '''
        
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    
    def get_stats(self) -> Dict:
        """Статистика по БД"""
        cursor = self.conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM messages')
        total_messages = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM message_metadata')
        processed_messages = cursor.fetchone()[0]
        
        cursor.execute('SELECT channel, COUNT(*) as cnt FROM messages GROUP BY channel')
        channel_stats = {row[0]: row[1] for row in cursor.fetchall()}
        
        return {
            'total_messages': total_messages,
            'processed_messages': processed_messages,
            'unprocessed_messages': total_messages - processed_messages,
            'channels': channel_stats
        }
    
    def close(self):
        """Закрытие соединения с БД"""
        if self.conn:
            self.conn.close()


class TelegramMessage:
    """Модель сообщения Telegram"""
    
    def __init__(self, channel: str, message_id: str, text: str, 
                 datetime: str = None, permalink: str = None, channel_category: str = None):
        self.channel = channel
        self.message_id = message_id
        self.text = text
        self.datetime = datetime
        self.permalink = permalink
        self.channel_category = channel_category
    
    def to_dict(self) -> Dict:
        """Конвертация в словарь"""
        # Базовая статистика
        words = self.text.split()
        word_count = len(words)
        char_count = len(self.text)
        has_links = bool(re.search(r'https?://', self.text))
        has_mentions = bool(re.search(r'@\w+', self.text))
        has_hashtags = bool(re.search(r'#\w+', self.text))
        
        return {
            'message_id': self.message_id,
            'channel': self.channel,
            'channel_category': self.channel_category,
            'text': self.text,
            'datetime': self.datetime,
            'permalink': self.permalink,
            'word_count': word_count,
            'char_count': char_count,
            'has_links': has_links,
            'has_mentions': has_mentions,
            'has_hashtags': has_hashtags
        }


class TelegramHTMLParser(HTMLParser):
    """Парсер HTML страниц Telegram"""
    
    def __init__(self) -> None:
        super().__init__()
        self.messages: List[TelegramMessage] = []
        self._current: Optional[TelegramMessage] = None
        self._in_message = False
        self._in_text = False
        self._div_depth = 0
        self._current_channel = None

    def handle_starttag(self, tag: str, attrs: List[tuple]) -> None:
        attrs_dict = dict(attrs)
        class_list = attrs_dict.get("class", "").split()

        if (not self._in_message and tag == "div" 
            and "tgme_widget_message" in class_list):
            self._in_message = True
            self._div_depth = 1
            self._current = TelegramMessage(
                channel=self._current_channel or "",
                message_id=attrs_dict.get("data-post"),
                text="",
                datetime=None,
                permalink=None
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
                if self._current and self._current.text.strip():
                    self.messages.append(self._current)
                self._current = None
                self._in_message = False

    def handle_data(self, data: str) -> None:
        if self._in_message and self._in_text and self._current is not None:
            text = html.unescape(data)
            self._current.text += text


class TelegramParser:
    """Основной класс парсера Telegram"""
    
    def __init__(self, db_path: str = "telegram_data.db"):
        self.db = TelegramDatabase(db_path)
    
    def _channel_slug(self, url: str) -> str:
        """Извлечение slug канала из URL"""
        parsed = urlparse(url)
        slug = parsed.path.strip("/").split("/")[0]
        if not slug:
            raise ValueError(f"Не могу извлечь название канала из: {url}")
        return slug
    
    def _fetch_html(self, url: str, timeout: int = 15) -> str:
        """Загрузка HTML страницы"""
        headers = {"User-Agent": "Mozilla/5.0 (compatible; TelegramParser/2.0)"}
        with urlopen(Request(url, headers=headers), timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="ignore")
    
    def clean_text(self, text: str) -> str:
        """Очистка текста от мусора"""
        if not text:
            return ""
        
        # 1. Удаляем эмодзи
        try:
            text = emoji.replace_emoji(text, replace='')
        except:
            emoji_pattern = re.compile("["
                u"\U0001F600-\U0001F64F"
                u"\U0001F300-\U0001F5FF"
                u"\U0001F680-\U0001F6FF"
                u"\U0001F1E0-\U0001F1FF"
                "]+", flags=re.UNICODE)
            text = emoji_pattern.sub('', text)
        
        # 2. Удаляем URL
        text = re.sub(r'https?://\S+|t\.me/\S+', '', text)
        
        # 3. Удаляем упоминания и хештеги
        text = re.sub(r'[@#]\w+', '', text)
        
        # 4. Удаляем рекламные фразы
        ad_phrases = [
            r'подписывайся', r'канал', r'ссылка\s*в\s*описании',
            r'реклама', r'промокод', r'партнер'
        ]
        for phrase in ad_phrases:
            text = re.sub(phrase, '', text, flags=re.IGNORECASE)
        
        # 5. Нормализуем пробелы
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def parse_channel(self, channel_url: str, category: str = None, 
                     limit: int = 100) -> int:
        """
        Парсинг одного канала
        Возвращает количество новых сообщений
        """
        slug = self._channel_slug(channel_url)
        feed_url = f"https://t.me/s/{slug}?embed=1&userpic=true"
        
        print(f"\n Парсинг канала: {slug} (категория: {category or 'общая'})")
        
        try:
            html_content = self._fetch_html(feed_url)
            
            parser = TelegramHTMLParser()
            parser._current_channel = slug
            parser.feed(html_content)
            parser.close()
            
            messages = parser.messages[-limit:] if limit else parser.messages
            
            # Фильтрация и сохранение
            new_count = 0
            duplicate_count = 0
            filtered_count = 0
            
            for msg in messages:
                msg.channel_category = category
                
                # Фильтр: минимум 50 символов и 5 слов
                if len(msg.text) < 50 or len(msg.text.split()) < 5:
                    filtered_count += 1
                    continue
                
                # Очистка текста
                msg_dict = msg.to_dict()
                msg_dict['text_cleaned'] = self.clean_text(msg.text)
                
                # Сохранение в БД
                message_id = self.db.insert_message(msg_dict)
                
                if message_id:
                    new_count += 1
                else:
                    duplicate_count += 1
            
            print(f"  ✅ Новых: {new_count} | Дубликатов: {duplicate_count} | Отфильтровано: {filtered_count}")
            return new_count
            
        except Exception as e:
            print(f"   Ошибка: {e}")
            return 0
    
    def parse_all_channels(self, limit_per_channel: int = 100, 
                          delay: float = 1.0) -> Dict:
        """
        Парсинг всех каналов из конфигурации
        """
        print("ПАРСИНГ TELEGRAM КАНАЛОВ")
        
        total_new = 0
        results = {}
        
        for category, channels in CHANNEL_CONFIG.items():
            print(f"\n Категория: {category}")
            
            for channel_url in channels:
                new_count = self.parse_channel(
                    channel_url, 
                    category=category, 
                    limit=limit_per_channel
                )
                total_new += new_count
                results[channel_url] = new_count
                
                # Задержка между запросами
                time.sleep(delay)
        
        print(f"✅ ПАРСИНГ ЗАВЕРШЁН")
        print(f"Всего новых сообщений: {total_new}")
        
        # Статистика БД
        stats = self.db.get_stats()
        print(f"\n Статистика базы данных:")
        print(f"  • Всего сообщений: {stats['total_messages']}")
        print(f"  • Обработано: {stats['processed_messages']}")
        print(f"  • Ожидает обработки: {stats['unprocessed_messages']}")
        print(f"\n По каналам:")
        for channel, count in stats['channels'].items():
            print(f"  • {channel}: {count}")
        
        return results
    
    def close(self):
        """Закрытие соединения с БД"""
        self.db.close()


# Пример использования
if __name__ == "__main__":
    parser = TelegramParser("telegram_data.db")
    
    # Парсим все каналы
    results = parser.parse_all_channels(limit_per_channel=50, delay=1.5)
    
    # Показываем необработанные сообщения
    unprocessed = parser.db.get_unprocessed_messages(limit=5)
    print(f"\n Примеры необработанных сообщений:")
    for msg in unprocessed[:3]:
        print(f"\n[{msg['channel']}] {msg['datetime']}")
        print(f"{msg['text'][:150]}...")
    
    parser.close()
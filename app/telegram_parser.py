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

# Настройки
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

class TelegramHTMLParser(HTMLParser):
    """Парсер HTML страниц Telegram"""
    def __init__(self) -> None:
        super().__init__()
        self.messages = []
        self._current = None
        self._in_message = False
        self._in_text = False
        self._div_depth = 0
        self._current_channel = None
    
    def handle_starttag(self, tag: str, attrs: List[tuple]) -> None:
        attrs_dict = dict(attrs)
        class_list = attrs_dict.get("class", "").split()
        
        if (not self._in_message and tag == "div" and "tgme_widget_message" in class_list):
            self._in_message = True
            self._div_depth = 1
            self._current = {
                "channel": self._current_channel or "",
                "message_id": attrs_dict.get("data-post", ""),
                "text": "",
                "datetime": None,
                "permalink": None
            }
            return
        
        if self._in_message and tag == "div":
            self._div_depth += 1
        
        if self._in_message and tag == "div" and "tgme_widget_message_text" in class_list:
            self._in_text = True
        
        if self._in_message and tag == "time":
            if attrs_dict.get("datetime"):
                self._current["datetime"] = attrs_dict["datetime"]
        
        if self._in_message and tag == "a":
            if "tgme_widget_message_date" in class_list and attrs_dict.get("href"):
                self._current["permalink"] = attrs_dict["href"]
    
    def handle_endtag(self, tag: str) -> None:
        if self._in_text and tag == "div":
            self._in_text = False
        
        if self._in_message and tag == "div":
            self._div_depth -= 1
            if self._div_depth == 0:
                if self._current and self._current["text"].strip():
                    self.messages.append(self._current)
                self._current = None
                self._in_message = False
    
    def handle_data(self, data: str) -> None:
        if self._in_message and self._in_text and self._current is not None:
            text = html.unescape(data)
            self._current["text"] += text

class TelegramParser:
    """Основной класс парсера Telegram"""
    
    def __init__(self, db_path: str = "telegram_data.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Инициализация БД"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        cursor = self.conn.cursor()
        
        # Таблица для сырых сообщений
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS raw_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel TEXT NOT NULL,
            message_id TEXT,
            text TEXT NOT NULL,
            text_cleaned TEXT,
            datetime TEXT,
            permalink TEXT,
            channel_category TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Индекс для дедупликации
        cursor.execute('''
        CREATE UNIQUE INDEX IF NOT EXISTS idx_channel_message 
        ON raw_messages(channel, message_id)
        ''')
        
        self.conn.commit()
    
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
        
        # Удаляем эмодзи
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
        
        # Удаляем URL
        text = re.sub(r'https?://\S+|t\.me/\S+', '', text)
        
        # Удаляем упоминания и хештеги
        text = re.sub(r'[@#]\w+', '', text)
        
        # Нормализуем пробелы
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def parse_channel(self, channel_url: str, category: str = None, limit: int = 100) -> int:
        """Парсинг одного канала"""
        slug = self._channel_slug(channel_url)
        feed_url = f"https://t.me/s/{slug}?embed=1&userpic=true"
        
        print(f"Парсинг канала: {slug} (категория: {category or 'общая'})")
        
        try:
            html_content = self._fetch_html(feed_url)
            parser = TelegramHTMLParser()
            parser._current_channel = slug
            parser.feed(html_content)
            parser.close()
            
            messages = parser.messages[-limit:] if limit else parser.messages
            new_count = 0
            
            for msg in messages:
                # Фильтрация: минимум 30 символов
                if len(msg["text"]) < 30:
                    continue
                
                # Очистка текста
                text_cleaned = self.clean_text(msg["text"])
                
                # Сохранение
                cursor = self.conn.cursor()
                try:
                    cursor.execute('''
                    INSERT OR IGNORE INTO raw_messages 
                    (channel, message_id, text, text_cleaned, datetime, permalink, channel_category)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        msg["channel"],
                        msg["message_id"],
                        msg["text"],
                        text_cleaned,
                        msg["datetime"],
                        msg["permalink"],
                        category
                    ))
                    
                    if cursor.rowcount > 0:
                        new_count += 1
                        
                except sqlite3.Error as e:
                    print(f"Ошибка сохранения: {e}")
            
            self.conn.commit()
            print(f"✅ Новых: {new_count} | Всего: {len(messages)}")
            return new_count
            
        except Exception as e:
            print(f"❌ Ошибка парсинга {slug}: {e}")
            return 0
    
    def parse_all_channels(self, limit_per_channel: int = 100, delay: float = 1.0) -> Dict:
        """Парсинг всех каналов из конфигурации"""
        print("=" * 50)
        print("НАЧАЛО ПАРСИНГА TELEGRAM КАНАЛОВ")
        print("=" * 50)
        
        total_new = 0
        results = {}
        
        for category, channels in CHANNEL_CONFIG.items():
            print(f"\n📂 Категория: {category}")
            
            for channel_url in channels:
                new_count = self.parse_channel(
                    channel_url,
                    category=category,
                    limit=limit_per_channel
                )
                
                total_new += new_count
                results[channel_url] = new_count
                
                # Задержка между запросами
                if channel_url != channels[-1]:  # Не ждать после последнего
                    time.sleep(delay)
        
        # Статистика
        cursor = self.conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM raw_messages')
        total_messages = cursor.fetchone()[0]
        
        print("\n" + "=" * 50)
        print(f"✅ ПАРСИНГ ЗАВЕРШЕН")
        print(f"• Новых сообщений: {total_new}")
        print(f"• Всего в базе: {total_messages}")
        print("=" * 50)
        
        return results
    
    def get_unprocessed_messages(self, limit: int = None) -> List[Dict]:
        """Получить сообщения, которые еще не обработаны AI"""
        cursor = self.conn.cursor()
        
        # Ищем сообщения, которых нет в основной таблице messages
        query = '''
        SELECT rm.* 
        FROM raw_messages rm
        LEFT JOIN messages m ON rm.channel = m.channel AND rm.message_id = m.message_id
        WHERE m.id IS NULL
        ORDER BY rm.datetime DESC
        '''
        
        if limit:
            query += f' LIMIT {limit}'
        
        cursor.execute(query)
        return [dict(row) for row in cursor.fetchall()]
    
    def get_stats(self) -> Dict:
        """Статистика парсера"""
        cursor = self.conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM raw_messages')
        total = cursor.fetchone()[0]
        
        cursor.execute('SELECT channel_category, COUNT(*) FROM raw_messages GROUP BY channel_category')
        by_category = dict(cursor.fetchall())
        
        cursor.execute('SELECT channel, COUNT(*) FROM raw_messages GROUP BY channel ORDER BY COUNT(*) DESC LIMIT 10')
        top_channels = dict(cursor.fetchall())
        
        return {
            "total_messages": total,
            "by_category": by_category,
            "top_channels": top_channels
        }
    
    def close(self):
        """Закрытие соединения"""
        if self.conn:
            self.conn.close()

# Утилита для переноса данных в основную БД
def migrate_to_main_db():
    """Перенос данных из raw_messages в основную базу"""
    from app.db import Database
    
    parser = TelegramParser()
    main_db = Database()
    
    # Получаем необработанные сообщения
    raw_messages = parser.get_unprocessed_messages()
    
    print(f"Перенос {len(raw_messages)} сообщений в основную БД...")
    
    for raw_msg in raw_messages:
        # Преобразуем в формат основной БД
        message_data = {
            "channel": raw_msg["channel"],
            "message_id": raw_msg["message_id"],
            "text": raw_msg["text"],
            "datetime": raw_msg["datetime"],
            "permalink": raw_msg["permalink"],
            "text_cleaned": raw_msg["text_cleaned"],
            "channel_category": raw_msg["channel_category"]
        }
        
        # Добавляем дополнительные поля
        words = message_data["text"].split()
        message_data["word_count"] = len(words)
        message_data["char_count"] = len(message_data["text"])
        message_data["has_links"] = bool(re.search(r'https?://', message_data["text"]))
        message_data["has_mentions"] = bool(re.search(r'@\w+', message_data["text"]))
        message_data["has_hashtags"] = bool(re.search(r'#\w+', message_data["text"]))
        
        # Сохраняем в основную БД
        msg_id = main_db.insert_message(message_data)
        if msg_id:
            print(f"✅ Перенесено: {raw_msg['channel']} - {raw_msg['message_id']}")
    
    parser.close()
    print("Перенос завершен!")

if __name__ == "__main__":
    # Для тестирования парсера
    parser = TelegramParser()
    parser.parse_all_channels(limit_per_channel=50, delay=1.0)
    
    # Показать статистику
    stats = parser.get_stats()
    print(f"\n📊 Статистика:")
    print(f"Всего сообщений: {stats['total_messages']}")
    print(f"По категориям: {stats['by_category']}")
    
    parser.close()
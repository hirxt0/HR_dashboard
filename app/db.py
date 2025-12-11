import sqlite3
import json
import re
from datetime import datetime
from typing import List, Dict, Optional
from app.config import DB_PATH

class Database:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init()

    def _init(self):
        c = self.conn.cursor()

        # Таблица сообщений
        c.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel TEXT,
            message_id TEXT,
            text TEXT,
            datetime TEXT,
            permalink TEXT,
            text_cleaned TEXT,
            channel_category TEXT,
            word_count INTEGER DEFAULT 0,
            char_count INTEGER DEFAULT 0,
            has_links BOOLEAN DEFAULT 0,
            has_mentions BOOLEAN DEFAULT 0,
            has_hashtags BOOLEAN DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )""")

        # Таблица метаданных
        c.execute("""
        CREATE TABLE IF NOT EXISTS metadata (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id INTEGER,
            tags TEXT,
            sentiment TEXT,
            sentiment_score REAL,
            is_insider INTEGER,
            insider_confidence REAL,
            processed_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(message_id) REFERENCES messages(id)
        )""")

        # Индексы для производительности
        c.execute("CREATE INDEX IF NOT EXISTS idx_channel ON messages(channel)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_datetime ON messages(datetime)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_metadata_message ON metadata(message_id)")
        
        self.conn.commit()
        print(f"✅ База данных инициализирована: {DB_PATH}")

    def insert_message(self, msg):
        c = self.conn.cursor()
        
        # Вычисляем дополнительные поля
        word_count = len(msg.get("text", "").split())
        char_count = len(msg.get("text", ""))
        has_links = bool(re.search(r'https?://', msg.get("text", "")))
        has_mentions = bool(re.search(r'@\w+', msg.get("text", "")))
        has_hashtags = bool(re.search(r'#\w+', msg.get("text", "")))
        
        c.execute("""
            INSERT INTO messages(
                channel, message_id, text, datetime, permalink, 
                text_cleaned, channel_category, word_count, char_count,
                has_links, has_mentions, has_hashtags
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            msg.get("channel"),
            msg.get("message_id"),
            msg.get("text"),
            msg.get("datetime"),
            msg.get("permalink"),
            msg.get("text_cleaned", msg.get("text", "")),
            msg.get("channel_category"),
            word_count,
            char_count,
            1 if has_links else 0,
            1 if has_mentions else 0,
            1 if has_hashtags else 0
        ))
        self.conn.commit()
        return c.lastrowid

    def insert_metadata(self, message_id, meta):
        c = self.conn.cursor()
        c.execute("""
            INSERT INTO metadata(
                message_id, tags, sentiment, sentiment_score, 
                is_insider, insider_confidence
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            message_id,
            json.dumps(meta.get("tags", []), ensure_ascii=False),
            meta.get("sentiment", "neutral"),
            meta.get("sentiment_score", 0.0),
            1 if meta.get("is_insider", False) else 0,
            meta.get("insider_confidence", 0.0)
        ))
        self.conn.commit()
        return c.lastrowid

    # ДОБАВЛЯЕМ НУЖНЫЕ МЕТОДЫ
    
    def get_unprocessed_messages(self, limit: int = None) -> List[Dict]:
        """
        Получить сообщения, которые еще не обработаны AI
        (нет записи в таблице metadata)
        """
        c = self.conn.cursor()
        
        query = """
        SELECT m.* 
        FROM messages m
        LEFT JOIN metadata md ON m.id = md.message_id
        WHERE md.id IS NULL
        ORDER BY m.datetime DESC
        """
        
        if limit:
            query += f" LIMIT {limit}"
        
        c.execute(query)
        return [dict(row) for row in c.fetchall()]

    def get_all_metadata(self):
        """
        Получить все сообщения с метаданными
        """
        c = self.conn.cursor()
        query = """
        SELECT m.*, md.tags, md.sentiment, md.sentiment_score, 
               md.is_insider, md.insider_confidence
        FROM messages m
        JOIN metadata md ON m.id = md.message_id
        ORDER BY m.datetime DESC
        """
        return [dict(r) for r in c.execute(query).fetchall()]

    def get_by_tags(self, tags):
        """
        Находит новости по количеству совпадений тегов
        """
        c = self.conn.cursor()
        
        query = """
        SELECT m.*, md.tags 
        FROM messages m
        JOIN metadata md ON m.id = md.message_id
        """
        
        rows = c.execute(query).fetchall()
        
        scored = []
        for r in rows:
            try:
                doc_tags = json.loads(r["tags"])
            except:
                doc_tags = []
            
            score = len(set(tags) & set(doc_tags))
            if score > 0:
                scored.append((score, dict(r)))
        
        scored.sort(reverse=True, key=lambda x: x[0])
        return [x[1] for x in scored[:5]]

    def get_stats(self) -> Dict:
        """
        Статистика по БД
        """
        c = self.conn.cursor()
        
        # Общая статистика
        c.execute("SELECT COUNT(*) FROM messages")
        total_messages = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM metadata")
        processed_messages = c.fetchone()[0]
        
        c.execute("SELECT COUNT(DISTINCT channel) FROM messages")
        channels_count = c.fetchone()[0]
        
        # Статистика по каналам
        c.execute("SELECT channel, COUNT(*) as cnt FROM messages GROUP BY channel ORDER BY cnt DESC LIMIT 10")
        channels = [{"channel": row[0], "count": row[1]} for row in c.fetchall()]
        
        # Статистика по датам
        c.execute("""
        SELECT DATE(datetime) as date, COUNT(*) as cnt 
        FROM messages 
        WHERE datetime IS NOT NULL 
        GROUP BY DATE(datetime) 
        ORDER BY date DESC 
        LIMIT 7
        """)
        dates = [{"date": row[0], "count": row[1]} for row in c.fetchall()]
        
        return {
            "total_messages": total_messages,
            "processed_messages": processed_messages,
            "unprocessed_messages": total_messages - processed_messages,
            "channels_count": channels_count,
            "channels": channels,
            "recent_dates": dates,
            "last_updated": datetime.now().isoformat()
        }

    def get_recent_messages(self, limit: int = 10) -> List[Dict]:
        """
        Получить последние сообщения
        """
        c = self.conn.cursor()
        c.execute("""
        SELECT m.*, md.tags, md.sentiment 
        FROM messages m
        LEFT JOIN metadata md ON m.id = md.message_id
        ORDER BY m.datetime DESC
        LIMIT ?
        """, (limit,))
        return [dict(row) for row in c.fetchall()]

    def search_messages(self, query: str, limit: int = 20) -> List[Dict]:
        """
        Поиск по тексту сообщений
        """
        c = self.conn.cursor()
        search_term = f"%{query}%"
        
        c.execute("""
        SELECT m.*, md.tags, md.sentiment 
        FROM messages m
        LEFT JOIN metadata md ON m.id = md.message_id
        WHERE m.text LIKE ? OR m.text_cleaned LIKE ?
        ORDER BY m.datetime DESC
        LIMIT ?
        """, (search_term, search_term, limit))
        
        return [dict(row) for row in c.fetchall()]

    def get_messages_by_channel(self, channel: str, limit: int = 20) -> List[Dict]:
        """
        Получить сообщения по конкретному каналу
        """
        c = self.conn.cursor()
        
        c.execute("""
        SELECT m.*, md.tags, md.sentiment 
        FROM messages m
        LEFT JOIN metadata md ON m.id = md.message_id
        WHERE m.channel = ?
        ORDER BY m.datetime DESC
        LIMIT ?
        """, (channel, limit))
        
        return [dict(row) for row in c.fetchall()]

    def get_signal_statistics(self):
        """
        Статистика для агрегатора сигналов
        """
        c = self.conn.cursor()
        
        # Получаем все данные с метаданными
        c.execute("""
        SELECT m.id, md.tags, md.sentiment, md.is_insider
        FROM messages m
        JOIN metadata md ON m.id = md.message_id
        """)
        
        return [dict(row) for row in c.fetchall()]

    def close(self):
        """Закрытие соединения с БД"""
        if self.conn:
            self.conn.close()
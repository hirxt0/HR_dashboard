import csv
from app.db import Database
from app.chunker import chunk_text
from app.gigachat_client import GigaChatClient

class Processor:
    def __init__(self):
        self.db = Database()
        self.giga = GigaChatClient()
        self.tags = self.load_taxonomy()

    def load_taxonomy(self):
        tags = []
        with open("taxonomy/tags.csv", encoding="utf-8") as f:
            r = csv.reader(f)
            for row in r:
                tags.append(row[0])
        return tags

    def process_message(self, msg):
        chunks = chunk_text(msg["text_cleaned"])

        all_tags = set()
        sentiments = []
        insiders = []

        for ch in chunks:
            cls = self.giga.classify_chunk(ch, self.tags)
            all_tags |= set(cls["tags"])
            sentiments.append(cls["sentiment_score"])
            insiders.append(cls["insider_confidence"] if cls["is_insider"] else 0)

        return {
            "tags": list(all_tags),
            "sentiment": (
                "positive" if sum(sentiments) > 0.2 else
                "negative" if sum(sentiments) < -0.2 else "neutral"
            ),
            "sentiment_score": sum(sentiments) / len(sentiments),
            "is_insider": any(i > 0.6 for i in insiders),
            "insider_confidence": max(insiders) if insiders else 0
        }

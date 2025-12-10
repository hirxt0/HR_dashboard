import os
import glob
import pandas as pd
import feedparser
from typing import List, Dict

def collect_from_folder(folder: str) -> List[Dict]:
    """
    Читает .txt и .csv файлы из папки.
    Возвращает список документов: {"id": str, "text": str, "source": str, "date": optional}
    """
    docs = []
    for path in glob.glob(os.path.join(folder, "**", "*.txt"), recursive=True):
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        docs.append({"id": os.path.basename(path), "text": text, "source": path})
    for path in glob.glob(os.path.join(folder, "**", "*.csv"), recursive=True):
        df = pd.read_csv(path)
        # ожидаем колонки text или content
        col = "text" if "text" in df.columns else ("content" if "content" in df.columns else None)
        if col is None:
            continue
        for idx, row in df.iterrows():
            docs.append({"id": f"{os.path.basename(path)}_{idx}", "text": str(row[col]), "source": path})
    return docs

def collect_from_rss(feeds: List[str], max_items: int = 50) -> List[Dict]:
    docs = []
    for feed in feeds:
        fr = feedparser.parse(feed)
        for e in fr.entries[:max_items]:
            text = e.get("summary", "") or e.get("description", "") or e.get("title", "")
            docs.append({"id": e.get("id", e.get("link", e.get("title"))), "text": text, "source": feed, "date": e.get("published")})
    return docs

from typing import List, Dict
from llm_client import LLMClient
import json
from tqdm import tqdm

class Classifier:
    def __init__(self, cfg, llm: LLMClient):
        self.cfg = cfg
        self.llm = llm

    def classify_chunks(self, chunks: List[Dict]) -> List[Dict]:
        """
        Для каждого чанка делаем:
          - тема (короткая классификация) -> Название темы
          - настроение -> positive/neutral/negative
          - теги -> comma separated
          - is_insight -> true/false
        В mock-режиме — возвращаются приближенные значения.
        """
        results = []
        prompts = []
        for c in chunks:
            prompt = f"""Текст чанка:
\"\"\"{c['text'][:2000]}\"\"\"

Задачи:
1) Определи краткую тему (5-10 слов) — "topic"
2) Определи настроение (sentiment): positive / neutral / negative
3) Вытащи до 5 ключевых тегов (tags), через запятую
4) Определи, является ли это инсайтом (insight): true/false

Отвечай в формате JSON:{{"topic":"...","sentiment":"...","tags":"...","insight":"..."}}
"""
            prompts.append(prompt)

        responses = self.llm.generate_batch(prompts)
        for c, r in zip(chunks, responses):
            # пытаемся распарсить JSON из ответа; если не получилось — fallback
            meta = {"topic": "", "sentiment": "neutral", "tags": "", "insight": "false"}
            try:
                import json
                parsed = json.loads(r.strip())
                for k in meta:
                    if k in parsed:
                        meta[k] = parsed[k]
            except Exception:
                # примитивный парсинг из текста
                text = r.lower()
                meta["topic"] = text.split("\n")[0][:100]
                if "negative" in text:
                    meta["sentiment"] = "negative"
                elif "positive" in text:
                    meta["sentiment"] = "positive"
                meta["tags"] = ",".join([t.strip() for t in text.split(",")[:5]])
                meta["insight"] = "true" if "true" in text or "инсайт" in text else "false"
            c["meta"] = meta
            results.append(c)
        return results

import numpy as np
from typing import List, Dict
import hdbscan
from sklearn.cluster import DBSCAN
from llm_client import LLMClient
import json

class Clusterer:
    def __init__(self, cfg, llm: LLMClient):
        self.cfg = cfg
        self.llm = llm

    def cluster(self, chunks: List[Dict]) -> List[Dict]:
        """
        Ожидаем что в каждом chunk есть 'n_embedding' (normalized).
        Добавляем поле cluster_id в каждый chunk.
        """
        embs = np.array([c["n_embedding"] for c in chunks])
        algo = self.cfg["clustering"].get("algorithm", "hdbscan")
        if algo == "hdbscan":
            min_size = self.cfg["clustering"].get("hdbscan_min_cluster_size", 5)
            model = hdbscan.HDBSCAN(min_cluster_size=min_size, prediction_data=True)
            labels = model.fit_predict(embs)
        else:
            eps = self.cfg["clustering"].get("dbscan_eps", 0.5)
            min_samples = self.cfg["clustering"].get("dbscan_min_samples", 5)
            model = DBSCAN(eps=eps, min_samples=min_samples, metric="cosine")
            labels = model.fit_predict(embs)

        for c, lab in zip(chunks, labels):
            c["cluster_id"] = int(lab)
        return chunks

    def name_clusters(self, chunks: List[Dict]) -> Dict[int, Dict]:
        """
        Собираем тексты из каждого кластера и просим LLM дать название (короткое и длинное).
        Возвращаем словарь cluster_id -> {name_short, name_long, size, top_tags, sentiment_summary}
        """
        clusters = {}
        # group
        by_cluster = {}
        for c in chunks:
            cid = c["cluster_id"]
            by_cluster.setdefault(cid, []).append(c)

        for cid, items in by_cluster.items():
            size = len(items)
            # создаём примеры текстов (до 10)
            sample_texts = "\n\n".join([it["text"][:1000] for it in items[:10]])
            prompt = f"""Даны примеры текстов кластера (до 10). Сформулируй:
1) Короткое название кластера (5-10 слов)
2) Длинное подробное название (15-30 слов)
3) Причины, почему тексты сгруппированы (список 3 пунктов)
Примеры:
{sample_texts}
Отвечай в JSON: {{"name_short":"...","name_long":"...","reason":["...","...","..."]}}
"""
            resp = self.llm.generate(prompt)
            try:
                parsed = json.loads(resp)
                name_short = parsed.get("name_short","").strip()
                name_long = parsed.get("name_long","").strip()
            except Exception:
                name_short = resp.split("\n")[0][:60]
                name_long = resp[:200]
            # aggregate tags & sentiment
            tags = {}
            sentiment_counts = {"positive":0,"neutral":0,"negative":0}
            for it in items:
                mt = it.get("meta",{})
                tgs = mt.get("tags","")
                for t in [x.strip() for x in tgs.split(",") if x.strip()]:
                    tags[t] = tags.get(t,0)+1
                s = mt.get("sentiment","neutral")
                sentiment_counts[s] = sentiment_counts.get(s,0)+1
            top_tags = sorted(tags.items(), key=lambda x:-x[1])[:5]
            clusters[cid] = {
                "name_short": name_short,
                "name_long": name_long,
                "size": size,
                "top_tags": [t for t,_ in top_tags],
                "sentiment_summary": sentiment_counts
            }
        return clusters

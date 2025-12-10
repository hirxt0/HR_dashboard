import numpy as np
from collections import Counter
from typing import List, Dict
from sklearn.cluster import DBSCAN
try:
    import hdbscan
    HDBSCAN_AVAILABLE = True
except ImportError:
    HDBSCAN_AVAILABLE = False

class Clusterer:
    def __init__(self, cfg, llm=None):
        self.cfg = cfg
        self.llm = llm
        self.algorithm = cfg["clustering"]["algorithm"]

    def cluster(self, chunks: List[Dict]) -> List[Dict]:
        """
        Кластеризует чанки на основе их эмбеддингов
        """
        print("КЛАСТЕРИЗАЦИЯ")
        print(f"Алгоритм: {self.algorithm}")
        print(f"Количество чанков: {len(chunks)}")
        
        embs = np.array([c["n_embedding"] for c in chunks])
        
        if self.algorithm == "hdbscan" and HDBSCAN_AVAILABLE:
            min_cluster_size = self.cfg["clustering"]["hdbscan_min_cluster_size"]
            clusterer = hdbscan.HDBSCAN(
                min_cluster_size=min_cluster_size,
                metric='euclidean'
            )
            labels = clusterer.fit_predict(embs)
        elif self.algorithm == "dbscan" or not HDBSCAN_AVAILABLE:
            eps = self.cfg["clustering"]["dbscan_eps"]
            min_samples = self.cfg["clustering"]["dbscan_min_samples"]
            clusterer = DBSCAN(eps=eps, min_samples=min_samples, metric='cosine')
            labels = clusterer.fit_predict(embs)
        else:
            raise ValueError(f"Unknown algorithm: {self.algorithm}")

        # Присваиваем cluster_id каждому чанку
        for i, c in enumerate(chunks):
            c["cluster_id"] = int(labels[i])
        
        # Статистика
        unique_clusters = set(labels)
        noise_count = sum(1 for l in labels if l == -1)
        
        print(f"\n Результаты кластеризации:")
        print(f"  • Найдено кластеров: {len(unique_clusters) - (1 if -1 in unique_clusters else 0)}")
        print(f"  • Шум (не вошли в кластеры): {noise_count} чанков")
        
        # Распределение по кластерам
        cluster_counts = Counter(labels)
        print(f"\n Распределение по кластерам:")
        for cluster_id in sorted(cluster_counts.keys()):
            if cluster_id != -1:
                count = cluster_counts[cluster_id]
                percentage = (count / len(chunks)) * 100
                print(f"  • Кластер {cluster_id:2d}: {count:3d} чанков ({percentage:5.1f}%)")
        
        if noise_count > 0:
            percentage = (noise_count / len(chunks)) * 100
            print(f"  • Шум      -1: {noise_count:3d} чанков ({percentage:5.1f}%)")
        
        
        return chunks

    def name_clusters(self, chunks: List[Dict]) -> Dict:
        """
        Генерирует названия и метаданные для каждого кластера
        """
        print("ИМЕНОВАНИЕ КЛАСТЕРОВ")
        
        clusters_map = {}
        for c in chunks:
            cid = c["cluster_id"]
            if cid not in clusters_map:
                clusters_map[cid] = []
            clusters_map[cid].append(c)

        result = {}
        
        for cid, cluster_chunks in clusters_map.items():
            print(f"\n🔸 Обработка кластера {cid} ({len(cluster_chunks)} чанков)...")
            
            if cid == -1:
                # Шум
                result[str(cid)] = {
                    "name_short": "Шум / Разное",
                    "name_long": "Чанки, не попавшие ни в один кластер",
                    "size": len(cluster_chunks),
                    "top_tags": []
                }
                print("  ✓ Кластер шума")
                continue

            # Собираем все теги из чанков кластера
            all_tags = []
            for ch in cluster_chunks:
                tags = ch.get("meta", {}).get("tags", [])
                
                # ИСПРАВЛЕНИЕ: Поддержка и строк и списков
                if isinstance(tags, str):
                    # Если это строка, разбиваем по запятой
                    tags = [t.strip() for t in tags.split(",") if t.strip()]
                elif isinstance(tags, list):
                    # Если это уже список, используем как есть
                    tags = [str(t).strip() for t in tags if t]
                else:
                    # Если неизвестный тип, пропускаем
                    tags = []
                
                all_tags.extend(tags)

            # Топ-5 тегов по частоте
            tag_counts = Counter(all_tags)
            top_tags = [tag for tag, _ in tag_counts.most_common(5)]

            # Собираем все категории
            categories = []
            sentiments = []
            for ch in cluster_chunks:
                meta = ch.get("meta", {})
                if "category" in meta:
                    categories.append(meta["category"])
                if "sentiment" in meta:
                    sentiments.append(meta["sentiment"])

            # Доминирующая категория
            if categories:
                main_category = Counter(categories).most_common(1)[0][0]
            else:
                main_category = "общее"
            
            # Доминирующая тональность
            if sentiments:
                main_sentiment = Counter(sentiments).most_common(1)[0][0]
            else:
                main_sentiment = "neutral"

            # Генерируем название через LLM (если real mode)
            if self.llm and self.llm.mode == "real":
                sample_texts = [ch["text"][:200] for ch in cluster_chunks[:3]]
                prompt = f"Дай короткое название (2-4 слова) для кластера новостей:\n\n"
                prompt += "\n---\n".join(sample_texts)
                prompt += f"\n\nТеги: {', '.join(top_tags[:5])}\nКатегория: {main_category}"
                
                try:
                    name_short = self.llm.generate(prompt).strip()
                except:
                    name_short = f"{main_category.capitalize()}"
            else:
                # Mock: просто используем категорию и топ тег
                if top_tags:
                    name_short = f"{main_category.capitalize()}: {top_tags[0]}"
                else:
                    name_short = main_category.capitalize()

            result[str(cid)] = {
                "name_short": name_short,
                "name_long": f"Кластер из {len(cluster_chunks)} чанков по теме '{main_category}'",
                "size": len(cluster_chunks),
                "top_tags": top_tags,
                "main_category": main_category,
                "main_sentiment": main_sentiment,
                "sentiment_distribution": dict(Counter(sentiments)) if sentiments else {}
            }
            
            print(f"  ✓ {name_short}")
            print(f"    Категория: {main_category}")
            print(f"    Тональность: {main_sentiment}")
            print(f"    Топ теги: {', '.join(top_tags[:3])}")

        print(f" Именование завершено: {len([k for k in result.keys() if k != '-1'])} кластеров")

        return result

    def get_cluster_summary(self, cluster_id: int, chunks: List[Dict]) -> Dict:
        """
        Возвращает детальную сводку по конкретному кластеру
        """
        cluster_chunks = [c for c in chunks if c.get("cluster_id") == cluster_id]
        
        if not cluster_chunks:
            return {"error": "cluster_not_found"}
        
        # Собираем статистику
        all_tags = []
        categories = []
        sentiments = []
        
        for ch in cluster_chunks:
            meta = ch.get("meta", {})
            
            # Обработка тегов (строка или список)
            tags = meta.get("tags", [])
            if isinstance(tags, str):
                tags = [t.strip() for t in tags.split(",") if t.strip()]
            elif isinstance(tags, list):
                tags = [str(t).strip() for t in tags if t]
            
            all_tags.extend(tags)
            
            if "category" in meta:
                categories.append(meta["category"])
            if "sentiment" in meta:
                sentiments.append(meta["sentiment"])
        
        return {
            "cluster_id": cluster_id,
            "size": len(cluster_chunks),
            "top_tags": [tag for tag, _ in Counter(all_tags).most_common(10)],
            "categories": dict(Counter(categories)),
            "sentiments": dict(Counter(sentiments)),
            "sample_texts": [ch["text"][:150] + "..." for ch in cluster_chunks[:3]]
        }
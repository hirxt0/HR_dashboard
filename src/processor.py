import os
from tqdm import tqdm
import json
from typing import List, Dict
import numpy as np

from embeddings import GetEmbeddings

class Processor:
    def __init__(self, cfg):
        self.cfg = cfg
        self.emb_model = GetEmbeddings(
            chunk_size=cfg["embeddings"]["chunk_size"],
            chunk_overlap=cfg["embeddings"]["chunk_overlap"],
            model_name=cfg["embeddings"]["model_name"]
        )
        self.batch_size = cfg["embeddings"].get("batch_size", 32)

    def docs_to_chunks(self, docs: List[Dict]) -> List[Dict]:
        """
        Преобразует список документов в чанки:
        возвращает список чанков: {"doc_id":..., "chunk_id":..., "text":...}
        """
        chunks = []
        for d in docs:
            text = d.get("text", "")
            pieces = self.emb_model.split(text)
            for i, p in enumerate(pieces):
                chunks.append({
                    "doc_id": d.get("id"),
                    "chunk_id": f"{d.get('id')}_chunk_{i}",
                    "text": p,
                    "source": d.get("source")
                })
        return chunks

    def embed_chunks(self, chunks: List[Dict]) -> List[Dict]:
        texts = [c["text"] for c in chunks]
        embs = self.emb_model.embedding(texts, batch_size=self.batch_size, normalize=True)
        for i, c in enumerate(chunks):
            c["embedding"] = embs[i].tolist()  # Нормализованные
            c["n_embedding"] = embs[i].tolist()  # Те же нормализованные (для обратной совместимости)
        
        return chunks
    
    def save_chunks(self, chunks: List[Dict], out_folder: str):
        os.makedirs(out_folder, exist_ok=True)
        path = os.path.join(out_folder, "chunks.jsonl")
        with open(path, "w", encoding="utf-8") as f:
            for c in chunks:
                f.write(json.dumps(c, ensure_ascii=False) + "\n")
        return path

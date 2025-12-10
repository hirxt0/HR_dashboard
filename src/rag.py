import faiss
import numpy as np
import os
import json
from typing import List, Dict

class RAG:
    def __init__(self, cfg):
        self.cfg = cfg
        self.index = None
        self.id_to_chunk = {}

    def build_index(self, chunks: List[Dict], out_folder: str):
        embs = np.array([c["n_embedding"] for c in chunks]).astype("float32")
        dim = embs.shape[1]
        index = faiss.IndexFlatIP(dim)  # cosine via normalized vectors -> inner product
        index.add(embs)
        self.index = index
        self.id_to_chunk = {i: chunks[i] for i in range(len(chunks))}
        os.makedirs(out_folder, exist_ok=True)
        faiss.write_index(index, os.path.join(out_folder, "faiss.index"))
        with open(os.path.join(out_folder, "id_map.json"), "w", encoding="utf-8") as f:
            json.dump({i: chunks[i]["chunk_id"] for i in range(len(chunks))}, f, ensure_ascii=False)
        return index

    def load_index(self, path_index: str, path_map: str):
        self.index = faiss.read_index(path_index)
        import json
        with open(path_map, "r", encoding="utf-8") as f:
            idmap = json.load(f)
        # id_to_chunk must be provided externally for full context — user may re-load chunks
        return idmap

    def query(self, query_emb, top_k=5):
        """
        query_emb: numpy array 1xd (normalized)
        """
        if self.index is None:
            raise ValueError("Index not built")
        q = np.array([query_emb]).astype("float32")
        D, I = self.index.search(q, top_k)
        idxs = I[0].tolist()
        scores = D[0].tolist()
        results = []
        for idx, sc in zip(idxs, scores):
            if idx == -1:
                continue
            chunk = self.id_to_chunk.get(idx)
            results.append({"chunk": chunk, "score": float(sc)})
        return results

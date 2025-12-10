import os
from utils import load_config, save_json
from collector import collect_from_folder, collect_from_rss
from processor import Processor
from llm_client import LLMClient
from classifier import Classifier
from clustering import Clusterer
from rag import RAG

def main(config_path="config.yaml"):
    cfg = load_config(config_path)
    out_folder = cfg["output"]["out_folder"]
    os.makedirs(out_folder, exist_ok=True)

    # 1) Collect
    docs = collect_from_folder(cfg["data"]["input_folder"])
    if cfg["data"].get("rss_feeds"):
        docs += collect_from_rss(cfg["data"]["rss_feeds"])

    print(f"Collected {len(docs)} documents.")

    # 2-3) Chunking + embeddings
    proc = Processor(cfg)
    chunks = proc.docs_to_chunks(docs)
    print(f"Generated {len(chunks)} chunks.")
    chunks = proc.embed_chunks(chunks)
    proc.save_chunks(chunks, out_folder)

    # 4) Classification via LLM
    llm = LLMClient(mode=cfg["llm"]["mode"], provider=cfg["llm"].get("provider"), api_key=cfg["llm"].get("api_key"))
    classifier = Classifier(cfg, llm)
    chunks = classifier.classify_chunks(chunks)

    # 5) Clustering
    clusterer = Clusterer(cfg, llm)
    chunks = clusterer.cluster(chunks)
    clusters_meta = clusterer.name_clusters(chunks)

    # save clusters meta
    save_json(clusters_meta, os.path.join(out_folder, "clusters.json"))
    save_json([{"chunk_id": c["chunk_id"], "cluster_id": c["cluster_id"], "meta": c.get("meta",{})} for c in chunks],
              os.path.join(out_folder, "chunks_clusters.json"))

    # 10) Build FAISS index for RAG
    rag = RAG(cfg)
    rag.build_index(chunks, os.path.join(out_folder, "indices"))

    print("Pipeline finished. Output in", out_folder)

if __name__ == "__main__":
    main()

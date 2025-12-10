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

    print("ЗАПУСК ПАЙПЛАЙНА")

    # 1) Collect
    print("\n Сбор данных...")
    docs = collect_from_folder(cfg["data"]["input_folder"])
    if cfg["data"].get("rss_feeds"):
        docs += collect_from_rss(cfg["data"]["rss_feeds"])
    print(f" Собрано {len(docs)} документов")

    # 2-3) Chunking + embeddings
    print("\n Разбивка на чанки и генерация эмбеддингов...")
    proc = Processor(cfg)
    chunks = proc.docs_to_chunks(docs)
    print(f" Создано {len(chunks)} чанков")
    
    chunks = proc.embed_chunks(chunks)
    print(f" Эмбеддинги сгенерированы")
    
    proc.save_chunks(chunks, out_folder)
    print(f" Чанки сохранены в {out_folder}/chunks.jsonl")

    # 4) Classification via MetadataProcessorRU or mock
    print("\n Классификация чанков...")
    llm = LLMClient(
        mode=cfg["llm"]["mode"], 
        provider=cfg["llm"].get("provider"), 
        api_key=cfg["llm"].get("api_key")
    )
    classifier = Classifier(cfg, llm)
    chunks = classifier.classify_chunks(chunks)
    
    # Сохраняем отчёт классификации
    classifier.save_classification_report(
        chunks, 
        os.path.join(out_folder, "classification_report.json")
    )

    # 5) Clustering
    print("\n Кластеризация...")
    clusterer = Clusterer(cfg, llm)
    chunks = clusterer.cluster(chunks)
    clusters_meta = clusterer.name_clusters(chunks)
    print(f" Создано {len([k for k in clusters_meta.keys() if k != '-1'])} кластеров")

    # Save clusters meta
    save_json(clusters_meta, os.path.join(out_folder, "clusters.json"))
    save_json(
        [{"chunk_id": c["chunk_id"], "cluster_id": c["cluster_id"], "meta": c.get("meta",{})} 
         for c in chunks],
        os.path.join(out_folder, "chunks_clusters.json")
    )
    print(f" Метаданные кластеров сохранены")

    # 6) Build FAISS index for RAG
    print("\n Построение FAISS индекса...")
    rag = RAG(cfg)
    rag.build_index(chunks, os.path.join(out_folder, "indices"))
    print(f" Индекс сохранён в {out_folder}/indices/")

    print(" ПАЙПЛАЙН ЗАВЕРШЁН УСПЕШНО!")
    print(f" Результаты: {out_folder}/")
    print(f"  • chunks.jsonl - чанки с эмбеддингами")
    print(f"  • classification_report.json - отчёт классификации")
    print(f"  • clusters.json - метаданные кластеров")
    print(f"  • chunks_clusters.json - привязка чанков к кластерам")
    print(f"  • indices/ - FAISS индекс для RAG")

if __name__ == "__main__":
    main()
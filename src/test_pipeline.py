import os
import json
import numpy as np
from run_pipeline import main

def create_test_data():
    """Создаем тестовые данные для проверки"""
    test_dir = "test_data"
    os.makedirs(test_dir, exist_ok=True)
    
    # 1. Создаем тестовые .txt файлы
    test_texts = [
        "Рынок IT в 2024 году показывает устойчивый рост. Крупные компании увеличивают инвестиции в AI.",
        "Проблемы с логистикой продолжают влиять на ценообразование в розничной торговле.",
        "Новый закон о налогообложении может повлиять на малый бизнес. Эксперты ожидают изменений.",
        "Криптовалюты демонстрируют волатильность после последних заявлений регуляторов.",
        "Зелёная энергетика получает поддержку государства. Инвестиции в солнечные панели растут."
    ]
    
    for i, text in enumerate(test_texts):
        with open(os.path.join(test_dir, f"doc_{i}.txt"), "w", encoding="utf-8") as f:
            f.write(text)
    
    # 2. Создаем тестовый .csv файл
    import pandas as pd
    csv_data = {
        "text": [
            "Финансовый отчёт компании показал прибыль выше ожиданий.",
            "Акции технологического сектора упали на 2% сегодня.",
            "Центробанк сохранил ключевую ставку без изменений."
        ],
        "source": ["news_1", "news_2", "news_3"]
    }
    df = pd.DataFrame(csv_data)
    df.to_csv(os.path.join(test_dir, "news.csv"), index=False, encoding="utf-8")
    
    return test_dir

def test_rag():
    """Тестируем RAG функциональность"""
    from embeddings import GetEmbeddings
    from rag import RAG
    
    # Создаем тестовые чанки
    emb_model = GetEmbeddings()
    texts = [
        "Искусственный интеллект трансформирует бизнес-процессы",
        "Машинное обучение помогает в анализе данных",
        "Нейросети используются для обработки естественного языка"
    ]
    
    # Получаем эмбеддинги
    embs = emb_model.normalized_embeddings(texts)
    
    # Тестируем RAG
    rag = RAG({"rag": {"top_k": 2}})
    
    chunks = [
        {"chunk_id": f"chunk_{i}", "text": text, "n_embedding": embs[i].tolist()}
        for i, text in enumerate(texts)
    ]
    
    # Строим индекс
    rag.build_index(chunks, "test_output")
    
    # Тестовый запрос
    query = "Как AI помогает в бизнесе?"
    query_emb = emb_model.normalized_embeddings([query])[0]
    
    results = rag.query(query_emb, top_k=2)
    print("\n=== RAG Тест ===")
    print(f"Запрос: {query}")
    print(f"Найденные результаты: {len(results)}")
    for r in results:
        print(f"- {r['chunk']['text'][:100]}... (score: {r['score']:.3f})")

def main_test():
    """Основная функция тестирования"""
    print("=== Начинаем тестирование пайплайна ===")
    
    # 1. Создаем тестовые данные
    print("\n1. Создание тестовых данных...")
    test_dir = create_test_data()
    
    # 2. Обновляем config.yaml для тестов
    config_content = f"""
data:
  input_folder: "{test_dir}"
  rss_feeds: []

embeddings:
  model_name: "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"  # Более легкая модель для тестов
  chunk_size: 400
  chunk_overlap: 100
  batch_size: 8

clustering:
  algorithm: "dbscan"  # Для небольших данных используем DBSCAN
  hdbscan_min_cluster_size: 2
  dbscan_eps: 0.3
  dbscan_min_samples: 2

llm:
  mode: "mock"
  provider: "gigachat"

rag:
  top_k: 3

output:
  out_folder: "test_output"
"""
    
    with open("test_config.yaml", "w", encoding="utf-8") as f:
        f.write(config_content)
    
    # 3. Запускаем пайплайн
    print("\n2. Запуск пайплайна...")
    try:
        main("test_config.yaml")
        print("✓ Пайплайн завершился успешно!")
    except Exception as e:
        print(f"✗ Ошибка в пайплайне: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 4. Проверяем результаты
    print("\n3. Проверка результатов...")
    
    output_files = [
        "test_output/chunks.jsonl",
        "test_output/clusters.json",
        "test_output/chunks_clusters.json",
        "test_output/indices/faiss.index"
    ]
    
    for file in output_files:
        if os.path.exists(file):
            print(f"✓ {file} создан")
            if file.endswith(".json"):
                try:
                    with open(file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    print(f"  Записей: {len(data) if isinstance(data, list) else 'dict'}")
                except:
                    pass
        else:
            print(f"✗ {file} не найден")
    
    # 5. Тест RAG
    print("\n4. Тестирование RAG...")
    try:
        test_rag()
        print("✓ RAG тест пройден")
    except Exception as e:
        print(f"✗ Ошибка в RAG тесте: {e}")
    
    # 6. Показываем кластеры
    clusters_file = "test_output/clusters.json"
    if os.path.exists(clusters_file):
        print("\n5. Результаты кластеризации:")
        with open(clusters_file, "r", encoding="utf-8") as f:
            clusters = json.load(f)
        
        for cluster_id, info in clusters.items():
            if cluster_id != "-1":  # Пропускаем шум
                print(f"\nКластер {cluster_id}:")
                print(f"  Название: {info.get('name_short', 'Н/Д')}")
                print(f"  Размер: {info.get('size', 0)}")
                print(f"  Теги: {', '.join(info.get('top_tags', []))}")
    
    print("\n=== Тестирование завершено ===")

if __name__ == "__main__":
    main_test()
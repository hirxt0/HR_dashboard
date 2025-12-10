import os
from dotenv import load_dotenv
import json
import numpy as np
from run_pipeline import main

load_dotenv()


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
        "Зелёная энергетика получает поддержку государства. Инвестиции в солнечные панели растут.",
        "В IT огромные проблемы"
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


def load_chunks_from_output(output_folder="test_output"):
    """Загружаем сгенерированные чанки из пайплайна"""
    chunks_file = os.path.join(output_folder, "chunks.jsonl")
    
    if not os.path.exists(chunks_file):
        raise FileNotFoundError(f"Файл {chunks_file} не найден. Запустите пайплайн сначала!")
    
    chunks = []
    with open(chunks_file, "r", encoding="utf-8") as f:
        for line in f:
            chunks.append(json.loads(line))
    
    return chunks


def generate_test_queries_from_data(chunks, n=5):
    """Генерируем тестовые запросы на основе реальных данных"""
    import random
    
    test_queries = []
    
    # Выбираем случайные чанки
    sample_chunks = random.sample(chunks, min(n, len(chunks)))
    
    for chunk in sample_chunks:
        text = chunk['text']
        
        # Извлекаем ключевые слова (первые слова предложений)
        sentences = text.split('.')
        if sentences:
            # Берём первое предложение и делаем из него вопрос
            first_sentence = sentences[0].strip()
            
            # Генерируем вопрос на основе контента
            if "IT" in text or "AI" in text or "технолог" in text:
                query = "Расскажи про развитие технологий и AI"
            elif "логистик" in text or "торговл" in text:
                query = "Какие проблемы в логистике и торговле?"
            elif "налог" in text or "закон" in text:
                query = "Что нового в законодательстве и налогах?"
            elif "криптовалют" in text or "регулятор" in text:
                query = "Ситуация с криптовалютами?"
            elif "энергетик" in text or "инвестиц" in text:
                query = "Инвестиции в энергетику?"
            else:
                # Общий вопрос
                query = f"Расскажи про {first_sentence[:50]}"
            
            test_queries.append({
                "query": query,
                "expected_chunk_id": chunk['chunk_id'],
                "expected_text": text[:100]
            })
    
    return test_queries


def test_rag_with_real_data(output_folder="test_output", config_path="test_config.yaml"):
    """Тестируем RAG с реальными данными из пайплайна"""
    from embeddings import GetEmbeddings
    from rag import RAG
    from utils import load_config
    
    print("\n" + "="*60)
    print("RAG ТЕСТИРОВАНИЕ С РЕАЛЬНЫМИ ДАННЫМИ")
    print("="*60)
    
    # 0. Загружаем конфиг чтобы использовать ту же модель
    cfg = load_config(config_path)
    
    # 1. Загружаем чанки из пайплайна
    print("\n📂 Загружаем данные из пайплайна...")
    chunks = load_chunks_from_output(output_folder)
    print(f"✓ Загружено {len(chunks)} чанков")
    
    # 2. Инициализируем RAG
    print("\n🔧 Инициализация RAG...")
    rag = RAG(cfg)
    
    # Загружаем существующий индекс
    index_path = os.path.join(output_folder, "indices", "faiss.index")
    map_path = os.path.join(output_folder, "indices", "id_map.json")
    
    if os.path.exists(index_path):
        rag.load_index(index_path, map_path)
        rag.id_to_chunk = {i: chunks[i] for i in range(len(chunks))}
        print("✓ FAISS индекс загружен")
    else:
        print("✗ Индекс не найден, создаём новый...")
        rag.build_index(chunks, os.path.join(output_folder, "indices"))
    
    # 3. Генерируем тестовые запросы из данных
    print("\n🎲 Генерируем тестовые запросы из ваших данных...")
    test_queries = generate_test_queries_from_data(chunks, n=5)
    
    # 4. Инициализируем embedder с той же моделью что и в конфиге
    print(f"\n🤖 Загружаем модель: {cfg['embeddings']['model_name']}")
    emb_model = GetEmbeddings(
        chunk_size=cfg["embeddings"]["chunk_size"],
        chunk_overlap=cfg["embeddings"]["chunk_overlap"],
        model_name=cfg["embeddings"]["model_name"]
    )
    
    # 5. Тестируем каждый запрос
    print("\n" + "="*60)
    print("РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ")
    print("="*60)
    
    total_tests = len(test_queries)
    passed_tests = 0
    
    for i, test in enumerate(test_queries, 1):
        query = test['query']
        expected_chunk_id = test['expected_chunk_id']
        
        print(f"\n{'─'*60}")
        print(f"ТЕСТ {i}/{total_tests}")
        print(f"{'─'*60}")
        print(f"📝 Запрос: {query}")
        print(f"🎯 Ожидаемый чанк: {expected_chunk_id}")
        
        # Получаем эмбеддинг запроса
        query_emb = emb_model.embedding([query])[0]
        
        # Выполняем поиск
        results = rag.query(query_emb, top_k=3)
        
        print(f"\n📊 Найдено результатов: {len(results)}")
        
        # Проверяем результаты
        found_expected = False
        for rank, r in enumerate(results, 1):
            chunk_id = r['chunk']['chunk_id']
            score = r['score']
            text_preview = r['chunk']['text'][:80]
            
            marker = "✓" if chunk_id == expected_chunk_id else " "
            print(f"\n{marker} Результат #{rank}:")
            print(f"   ID: {chunk_id}")
            print(f"   Score: {score:.4f}")
            print(f"   Текст: {text_preview}...")
            
            if chunk_id == expected_chunk_id:
                found_expected = True
                print(f"   🎉 НАЙДЕН ожидаемый чанк на позиции {rank}!")
        
        if found_expected:
            passed_tests += 1
            print(f"\n✅ Тест {i} ПРОЙДЕН")
        else:
            print(f"\n❌ Тест {i} НЕ ПРОЙДЕН (ожидаемый чанк не в топ-3)")
    
    # 6. Итоговая статистика
    print("\n" + "="*60)
    print("ИТОГОВАЯ СТАТИСТИКА")
    print("="*60)
    print(f"Всего тестов: {total_tests}")
    print(f"Пройдено: {passed_tests}")
    print(f"Провалено: {total_tests - passed_tests}")
    print(f"Успешность: {(passed_tests/total_tests)*100:.1f}%")
    
    if passed_tests == total_tests:
        print("\n🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
    elif passed_tests >= total_tests * 0.6:
        print("\n✓ Результат приемлемый для хакатона")
    else:
        print("\n⚠ Требуется улучшение RAG системы")


def interactive_rag_test(output_folder="test_output", config_path="test_config.yaml"):
    """Интерактивное тестирование RAG"""
    from embeddings import GetEmbeddings
    from rag import RAG
    from utils import load_config
    
    print("\n" + "="*60)
    print("ИНТЕРАКТИВНОЕ ТЕСТИРОВАНИЕ RAG")
    print("="*60)
    print("Введите свои запросы для тестирования RAG системы")
    print("Для выхода введите 'exit' или 'quit'")
    print("="*60)
    
    # Загружаем конфиг
    cfg = load_config(config_path)
    
    # Загружаем данные
    chunks = load_chunks_from_output(output_folder)
    
    # Инициализируем RAG
    rag = RAG(cfg)
    index_path = os.path.join(output_folder, "indices", "faiss.index")
    map_path = os.path.join(output_folder, "indices", "id_map.json")
    
    rag.load_index(index_path, map_path)
    rag.id_to_chunk = {i: chunks[i] for i in range(len(chunks))}
    
    # Используем ту же модель что и в конфиге
    emb_model = GetEmbeddings(
        chunk_size=cfg["embeddings"]["chunk_size"],
        chunk_overlap=cfg["embeddings"]["chunk_overlap"],
        model_name=cfg["embeddings"]["model_name"]
    )
    
    while True:
        query = input("\n🔍 Ваш запрос: ").strip()
        
        if query.lower() in ['exit', 'quit', 'выход']:
            print("👋 До свидания!")
            break
        
        if not query:
            continue
        
        # Поиск
        query_emb = emb_model.embedding([query])[0]
        results = rag.query(query_emb, top_k=5)
        
        print(f"\n📊 Найдено {len(results)} результатов:\n")
        
        for i, r in enumerate(results, 1):
            print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            print(f"Результат #{i} (score: {r['score']:.4f})")
            print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            print(f"ID: {r['chunk']['chunk_id']}")
            print(f"Текст: {r['chunk']['text']}")
            print()


def main_test():
    """Основная функция тестирования"""
    print("="*60)
    print("НАЧАЛО ТЕСТИРОВАНИЯ ПАЙПЛАЙНА")
    print("="*60)
    
    # 1. Создаем тестовые данные
    print("\n1️⃣ Создание тестовых данных...")
    test_dir = create_test_data()
    print(f"✓ Тестовые данные созданы в {test_dir}")
    
    # 2. Обновляем config для тестов
    config_content = f"""data:
  input_folder: "{test_dir}"
  rss_feeds: []

embeddings:
  model_name: "sentence-transformers/all-mpnet-base-v2"  # ← ТАКАЯ ЖЕ КАК В ОСНОВНОМ CONFIG!
  chunk_size: 400
  chunk_overlap: 100
  batch_size: 8

clustering:
  algorithm: "dbscan"
  hdbscan_min_cluster_size: 2
  dbscan_eps: 0.3
  dbscan_min_samples: 2

llm:
  mode: "mock"
  provider: "gigachat"

rag:
  top_k: 3
  min_score: 0.0

output:
  out_folder: "test_output"
"""
    
    with open("test_config.yaml", "w", encoding="utf-8") as f:
        f.write(config_content)
    print("✓ Конфигурация для тестов создана")
    
    # 3. Запускаем пайплайн
    print("\n2️⃣ Запуск пайплайна...")
    try:
        main("test_config.yaml")
        print("✓ Пайплайн завершился успешно!")
    except Exception as e:
        print(f"✗ Ошибка в пайплайне: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 4. Проверяем результаты
    print("\n3️⃣ Проверка выходных файлов...")
    output_files = [
        "test_output/chunks.jsonl",
        "test_output/clusters.json",
        "test_output/chunks_clusters.json",
        "test_output/indices/faiss.index"
    ]
    
    for file in output_files:
        if os.path.exists(file):
            print(f"✓ {file}")
            if file.endswith(".json"):
                try:
                    with open(file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    print(f"  └─ Записей: {len(data) if isinstance(data, list) else 'dict'}")
                except:
                    pass
        else:
            print(f"✗ {file} не найден")
    
    # 5. Тестируем RAG с реальными данными
    print("\n4️⃣ Тестирование RAG с реальными данными...")
    try:
        test_rag_with_real_data("test_output", "test_config.yaml")  # ← Передаём путь к конфигу
    except Exception as e:
        print(f"✗ Ошибка в RAG тесте: {e}")
        import traceback
        traceback.print_exc()
    
    # 6. Показываем кластеры
    clusters_file = "test_output/clusters.json"
    if os.path.exists(clusters_file):
        print("\n5️⃣ Результаты кластеризации:")
        with open(clusters_file, "r", encoding="utf-8") as f:
            clusters = json.load(f)
        
        for cluster_id, info in clusters.items():
            if cluster_id != "-1":
                print(f"\n🔸 Кластер {cluster_id}:")
                print(f"   Название: {info.get('name_short', 'Н/Д')}")
                print(f"   Размер: {info.get('size', 0)}")
                print(f"   Теги: {', '.join(info.get('top_tags', []))}")
    
    # 7. Предложить интерактивный режим
    print("\n" + "="*60)
    print("ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
    print("="*60)
    
    answer = input("\n💡 Хотите протестировать RAG в интерактивном режиме? (y/n): ")
    if answer.lower() in ['y', 'yes', 'д', 'да']:
        interactive_rag_test("test_output", "test_config.yaml")


if __name__ == "__main__":
    main_test()
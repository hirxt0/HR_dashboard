# test.py
import os
from classifier import LLMMetadataClassifier

# Тестовые тексты для анализа
TEST_TEXTS = [
    """Искусственный интеллект продолжает революционизировать различные отрасли. 
    Новые алгоритмы машинного обучения позволяют анализировать огромные объемы данных 
    и делать точные прогнозы. Крупные компании инвестируют миллиарды в развитие ИИ, 
    что создает новые возможности для стартапов и исследователей.""",
    
    """Финансовые рынки демонстрируют нестабильность на фоне геополитической 
    напряженности. Инвесторы проявляют осторожность, что сказывается на инвестициях 
    в технологический сектор. Эксперты прогнозируют возможный кризис в ближайшие месяцы.""",
    
    """Новые подходы к онлайн-обучению меняют традиционное образование. 
    Университеты внедряют интерактивные платформы, которые позволяют студентам 
    со всего мира получать качественные знания. Это открывает прекрасные перспективы 
    для развития науки и исследований.""",
    
    """Молодые предприниматели создают инновационные стартапы в сфере 
    технологий и маркетинга. Несмотря на сложности с финансированием, многие 
    проекты находят поддержку у инвесторов и демонстрируют хорошие результаты.""",
]

def test_without_db():
    """Тестирование классификатора без БД"""
    
    # Получаем API ключ из переменных окружения
    api_key = os.getenv("GROQ_API_KEY")
    
    if not api_key:
        print("❌ Ошибка: GROQ_API_KEY не найден в переменных окружения")
        print("📝 Создайте файл .env с содержимым: GROQ_API_KEY=ваш_ключ")
        print("💡 Или установите переменную окружения: export GROQ_API_KEY=ваш_ключ")
        return
    
    print("=" * 70)
    print("🧪 ТЕСТИРОВАНИЕ КЛАССИФИКАТОРА С LLM")
    print("📌 LLM выбирает теги из заданного списка с объяснением")
    print("=" * 70)
    
    # Создаем классификатор без БД
    classifier = LLMMetadataClassifier(db_path=None, api_key=api_key)
    
    # Выводим доступные теги
    print(f"\n📋 Доступные теги для выбора ({len(classifier.PREDEFINED_TAGS)}):")
    print(", ".join(classifier.PREDEFINED_TAGS[:15]) + "...")
    
    # Тестируем на разных текстах
    for i, text in enumerate(TEST_TEXTS, 1):
        print(f"\n{'='*70}")
        print(f"🧪 ТЕСТ {i}")
        print(f"{'='*70}")
        
        try:
            # Анализируем текст
            result = classifier.analyze_text(text)
            
        except Exception as e:
            print(f"❌ Ошибка при анализе: {e}")
        
        # Пауза между запросами
        if i < len(TEST_TEXTS):
            print("\n" + "-"*50)
            input("⏸️  Нажмите Enter для продолжения...")

def test_with_custom_text():
    """Тестирование с произвольным текстом от пользователя"""
    
    api_key = os.getenv("GROQ_API_KEY")
    
    if not api_key:
        print("❌ Ошибка: GROQ_API_KEY не найден")
        return
    
    classifier = LLMMetadataClassifier(db_path=None, api_key=api_key)
    
    print("\n" + "="*70)
    print("✍️  ТЕСТИРОВАНИЕ С ВАШИМ ТЕКСТОМ")
    print("="*70)
    
    while True:
        print("\n📝 Введите текст для анализа (или 'exit' для выхода):")
        user_text = input("> ")
        
        if user_text.lower() == 'exit':
            break
        
        if len(user_text.strip()) < 10:
            print("⚠️  Текст слишком короткий. Минимум 10 символов.")
            continue
        
        try:
            result = classifier.analyze_text(user_text)
            
        except Exception as e:
            print(f"❌ Ошибка при анализе: {e}")

def create_test_db():
    """Создание тестовой БД для проверки работы с данными"""
    import sqlite3
    import json
    
    print("\n🗄️  Создание тестовой БД...")
    
    # Удаляем старую БД если есть
    if os.path.exists("test_telegram_data.db"):
        os.remove("test_telegram_data.db")
    
    # Создаем БД и таблицу
    conn = sqlite3.connect("test_telegram_data.db")
    cursor = conn.cursor()
    
    # Создаем таблицу chunks
    cursor.execute("""
    CREATE TABLE chunks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        text TEXT NOT NULL,
        metadata TEXT,
        llm_tags TEXT,
        sentiment TEXT,
        explanation TEXT
    )
    """)
    
    # Добавляем тестовые данные
    for i, text in enumerate(TEST_TEXTS, 1):
        cursor.execute("""
        INSERT INTO chunks (text, metadata) 
        VALUES (?, ?)
        """, (
            text,
            json.dumps({"source": "test", "id": i})
        ))
    
    conn.commit()
    conn.close()
    
    print(f"✅ Создана тестовая БД: test_telegram_data.db")
    print(f"📊 Добавлено {len(TEST_TEXTS)} тестовых записей")
    
    return "test_telegram_data.db"

def test_with_db(db_path, limit=None):
    """Тестирование с БД"""
    import sqlite3
    
    api_key = os.getenv("GROQ_API_KEY")
    
    if not api_key or api_key == "ваш_ключ_здесь":
        print("❌ API ключ не настроен")
        return
    
    print(f"\n🗄️  Тестирование с БД: {db_path}")
    print(f"📊 Лимит обработки: {'все' if limit is None else limit} записей")
    
    classifier = LLMMetadataClassifier(
        db_path=db_path, 
        api_key=api_key
    )
    
    # Проверяем сколько записей в БД
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM chunks")
    total_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM chunks WHERE llm_tags IS NOT NULL")
    processed_count = cursor.fetchone()[0]
    conn.close()
    
    print(f"📈 Всего записей: {total_count}")
    print(f"✅ Уже обработано: {processed_count}")
    print(f"⏳ Осталось обработать: {total_count - processed_count}")
    
    results = classifier.process_all(limit=limit, delay=1.0)
    
    if results:
        print(f"\n🎉 Успешно обработано: {len(results)} записей")
        
        # Показываем результаты
        print(f"\n📋 Результаты:")
        for result in results:
            print(f"\n🧩 Чанк {result['chunk_id']}:")
            print(f"   🏷️  Теги: {', '.join(result['llm_tags'])}")
            print(f"   😊 Настроение: {result['sentiment']}")
            print(f"   📝 Объяснение: {result['explanation'][:100]}...")
        
        return results
    else:
        print("⚠️  Не удалось обработать записи")
        return []

def main():
    """Основная функция тестирования"""
    
    # Создаем файл .env если его нет
    if not os.path.exists(".env"):
        with open(".env", "w") as f:
            f.write("# Добавьте ваш API ключ Groq\n")
            f.write("# Получите ключ на https://console.groq.com/api-keys\n")
            f.write("GROQ_API_KEY=ваш_ключ_здесь\n")
        print("📝 Создан файл .env. Добавьте ваш GROQ_API_KEY в этот файл.")
        return
    
    # Читаем API ключ
    from dotenv import load_dotenv
    load_dotenv()
    
    api_key = os.getenv("GROQ_API_KEY")
    
    if not api_key or api_key == "ваш_ключ_здесь":
        print("❌ Ошибка: GROQ_API_KEY не настроен")
        print("📝 Откройте файл .env и замените 'ваш_ключ_здесь' на ваш настоящий API ключ")
        return
    
    print("=" * 70)
    print("🧪 ТЕСТИРОВАНИЕ КЛАССИФИКАТОРА МЕТАДАННЫХ")
    print("📌 Теги + Настроение + Объяснение")
    print("=" * 70)
    
    test_db_path = None
    
    while True:
        print("\n🎮 Выберите действие:")
        print("1. 🧪 Тестирование на предустановленных текстах (без БД)")
        print("2. ✍️  Тестирование с вашим текстом (без БД)")
        print("3. 🗄️  Создать тестовую БД")
        print("4. 🔄 Обработать ВСЕ записи из БД")
        print("5. ⚡ Обработать 2 записи из БД (быстрый тест)")
        print("6. 📊 Показать статистику БД")
        print("7. 🚪 Выход")
        
        choice = input("👉 Ваш выбор (1-7): ").strip()
        
        if choice == "1":
            test_without_db()
        elif choice == "2":
            test_with_custom_text()
        elif choice == "3":
            test_db_path = create_test_db()
        elif choice == "4":
            if test_db_path or os.path.exists("test_telegram_data.db"):
                db_path = test_db_path or "test_telegram_data.db"
                test_with_db(db_path, limit=None)
            else:
                print("⚠️  Сначала создайте тестовую БД (опция 3)")
        elif choice == "5":
            if test_db_path or os.path.exists("test_telegram_data.db"):
                db_path = test_db_path or "test_telegram_data.db"
                test_with_db(db_path, limit=2)
            else:
                print("⚠️  Сначала создайте тестовую БД (опция 3)")
        elif choice == "6":
            show_db_stats()
        elif choice == "7":
            print("👋 Выход...")
            break
        else:
            print("❌ Неверный выбор. Попробуйте снова.")

def show_db_stats():
    """Показать статистику БД"""
    import sqlite3
    import json
    
    db_path = "test_telegram_data.db"
    if not os.path.exists(db_path):
        print("⚠️  Тестовая БД не найдена.")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Общая статистика
    cursor.execute("SELECT COUNT(*) FROM chunks")
    total = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM chunks WHERE llm_tags IS NOT NULL")
    processed = cursor.fetchone()[0]
    
    # Статистика по настроениям
    cursor.execute("SELECT sentiment, COUNT(*) FROM chunks WHERE sentiment IS NOT NULL GROUP BY sentiment")
    sentiments = cursor.fetchall()
    
    print(f"\n📊 Статистика БД:")
    print(f"📈 Всего записей: {total}")
    print(f"✅ Обработано: {processed}")
    print(f"⏳ Не обработано: {total - processed}")
    
    if processed > 0:
        print(f"📈 Процент обработки: {processed/total*100:.1f}%")
    
    if sentiments:
        print(f"\n😊 Распределение настроений:")
        for sentiment, count in sentiments:
            print(f"   {sentiment}: {count} ({count/processed*100:.1f}%)")
    
    # Примеры результатов
    cursor.execute("""
        SELECT llm_tags, sentiment, explanation 
        FROM chunks 
        WHERE llm_tags IS NOT NULL 
        LIMIT 3
    """)
    examples = cursor.fetchall()
    
    if examples:
        print(f"\n📋 Примеры результатов:")
        for i, (tags_json, sentiment, explanation) in enumerate(examples, 1):
            try:
                tags = json.loads(tags_json)
                print(f"\n   Пример {i}:")
                print(f"      🏷️  Теги: {', '.join(tags)}")
                print(f"      😊 Настроение: {sentiment}")
                print(f"      📝 Объяснение: {explanation[:80]}...")
            except:
                print(f"\n   Пример {i}: ошибка чтения данных")
    
    conn.close()

if __name__ == "__main__":
    main()
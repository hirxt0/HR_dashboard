"""
pipeline.py - Создание БД с реалистичными новостями и запуск LLM классификации
"""
import os
import sys
import time
from datetime import datetime
import json
import sqlite3

def print_step(step_num, description):
    """Красивый вывод шагов"""
    print(f"\n{'='*60}")
    print(f"📋 ШАП {step_num}: {description}")
    print(f"{'='*60}")

class DataPipeline:
    def __init__(self):
        self.db_path = "telegram_data.db"
        
    def run_full_pipeline(self):
        """Запуск полного пайплайна"""
        print("🚀 ЗАПУСК ПАЙПЛАЙНА: СОЗДАНИЕ БАЗЫ ДАННЫХ И LLM КЛАССИФИКАЦИЯ")
        print("=" * 70)
        
        # Шаг 1: Создание БД с реалистичными новостями
        self.step1_create_realistic_database()
        
        # Шаг 2: Анализ через LLM (теги, настроение, объяснение)
        self.step2_llm_classification()
        
        # Шаг 3: Быстрый анализ трендов
        self.step3_basic_trend_analysis()
        
        print("\n" + "=" * 70)
        print("✅ ПАЙПЛАЙН УСПЕШНО ЗАВЕРШЕН!")
        print("=" * 70)
        print("\n📋 Что сделано:")
        print("1. 📁 Создана база данных с 50 реалистичными новостями")
        print("2. 🧠 Все новости проанализированы через LLM (теги, настроение)")
        print("3. 📈 Проведен базовый анализ трендов")
        print("\n🚀 Для запуска дашборда выполните: python app.py")
        print("🌐 Затем откройте в браузере: http://localhost:5000")
    
    def step1_create_realistic_database(self):
        """Шаг 1: Создание БД с реалистичными новостями"""
        print_step(1, "Создание базы данных с реалистичными новостями")
        
        from database import init_database, create_realistic_news
        
        print("🗄️  Инициализация базы данных...")
        init_database()
        
        print("📝 Создание реалистичных новостей для анализа...")
        create_realistic_news()
        
        # Проверяем результат
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM chunks")
        total = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM chunks WHERE llm_tags IS NOT NULL")
        classified = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM chunks WHERE sentiment IS NOT NULL")
        with_sentiment = cursor.fetchone()[0]
        
        conn.close()
        
        print(f"✅ База данных создана: {total} новостей")
        print(f"📊 Статистика:")
        print(f"   • Всего новостей: {total}")
        print(f"   • С тегами (LLM): {classified}")
        print(f"   • С настроением: {with_sentiment}")
    
    def step2_llm_classification(self):
        """Шаг 2: Анализ всех новостей через LLM"""
        print_step(2, "Анализ новостей через LLM (генерация тегов и настроения)")
        
        try:
            from classifier import LLMMetadataClassifier
            
            # Проверяем API ключ
            api_key = os.getenv("GROQ_API_KEY")
            if not api_key or api_key == "ваш_ключ_здесь":
                print("⚠️  GROQ_API_KEY не настроен!")
                print("❌ Без API ключа LLM не сможет проанализировать новости")
                print("ℹ️  Заполните .env файл и запустите пайплайн снова")
                return
            
            print("🧠 Запуск LLM классификатора для анализа новостей...")
            print("ℹ️  LLM будет анализировать каждую новость и генерировать:")
            print("   • 3-5 релевантных тегов")
            print("   • Настроение (positive/neutral/negative)")
            print("   • Краткое объяснение выбора тегов")
            
            # Инициализируем классификатор
            classifier = LLMMetadataClassifier(
                db_path=self.db_path,
                api_key=api_key
            )
            
            # Получаем ВСЕ новости без тегов
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM chunks WHERE llm_tags IS NULL")
            unclassified_count = cursor.fetchone()[0]
            conn.close()
            
            if unclassified_count == 0:
                print("✅ Все новости уже проанализированы через LLM")
                return
            
            print(f"📝 Найдено {unclassified_count} новостей для анализа через LLM...")
            
            # Обрабатываем порциями по 10 новостей
            batch_size = 10
            total_processed = 0
            
            while True:
                chunks = classifier.get_chunks(limit=batch_size)
                if not chunks:
                    break
                
                print(f"\n🔄 Обработка {len(chunks)} новостей (пакет {total_processed//batch_size + 1})...")
                
                results = []
                for i, chunk in enumerate(chunks, 1):
                    try:
                        print(f"   📰 Новость {total_processed + i}: {chunk.text[:80]}...")
                        
                        # Анализ через LLM
                        llm_tags, sentiment, explanation = classifier.analyze_with_llm(chunk.text)
                        
                        # Сохраняем в БД
                        classifier.save_to_db(
                            chunk.chunk_id, 
                            llm_tags, 
                            sentiment, 
                            explanation
                        )
                        
                        results.append({
                            'id': chunk.chunk_id,
                            'tags': llm_tags,
                            'sentiment': sentiment
                        })
                        
                        print(f"     ✅ Теги: {', '.join(llm_tags[:3])}")
                        print(f"     😊 Настроение: {sentiment}")
                        
                        # Задержка чтобы не превысить rate limit
                        time.sleep(1.5)
                        
                    except Exception as e:
                        print(f"     ❌ Ошибка: {e}")
                        continue
                
                total_processed += len(chunks)
                print(f"📊 Обработано: {total_processed}/{unclassified_count}")
                
                if len(chunks) < batch_size:
                    break
            
            # Статистика
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT sentiment, COUNT(*) FROM chunks WHERE sentiment IS NOT NULL GROUP BY sentiment")
            sentiment_stats = cursor.fetchall()
            
            cursor.execute('''SELECT COUNT(DISTINCT json_each.value) 
                            FROM chunks, json_each(llm_tags) 
                            WHERE llm_tags IS NOT NULL''')
            unique_tags = cursor.fetchone()[0]
            
            conn.close()
            
            print(f"\n📊 Результаты LLM классификации:")
            print(f"   • Обработано новостей: {total_processed}")
            print(f"   • Уникальных тегов: {unique_tags}")
            print(f"   • Распределение настроений:")
            for sentiment, count in sentiment_stats:
                print(f"     - {sentiment}: {count}")
            
            print("✅ LLM классификация завершена!")
            
        except Exception as e:
            print(f"❌ Ошибка в LLM классификации: {e}")
            import traceback
            traceback.print_exc()
    
    def step3_basic_trend_analysis(self):
        """Шаг 3: Быстрый анализ трендов"""
        print_step(3, "Базовый анализ трендов")
        
        try:
            print("📈 Анализ популярных тегов и трендов...")
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Самые популярные теги
            cursor.execute('''
            SELECT json_each.value as tag, COUNT(*) as count
            FROM chunks, json_each(llm_tags)
            WHERE llm_tags IS NOT NULL
            GROUP BY tag
            ORDER BY count DESC
            LIMIT 15
            ''')
            
            popular_tags = cursor.fetchall()
            
            print(f"🏷️  Топ-15 самых популярных тегов:")
            for i, (tag, count) in enumerate(popular_tags, 1):
                print(f"   {i:2}. {tag:<25} - {count:2} упоминаний")
            
            # Анализ по настроениям
            cursor.execute('''
            SELECT 
                sentiment,
                COUNT(*) as count,
                ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM chunks WHERE sentiment IS NOT NULL), 1) as percentage
            FROM chunks 
            WHERE sentiment IS NOT NULL
            GROUP BY sentiment
            ORDER BY count DESC
            ''')
            
            sentiment_stats = cursor.fetchall()
            
            print(f"\n😊 Распределение настроений:")
            for sentiment, count, percentage in sentiment_stats:
                print(f"   • {sentiment}: {count} новостей ({percentage}%)")
            
            # Тренды по датам
            cursor.execute('''
            SELECT 
                strftime('%Y-%m-%d', created_at) as date,
                COUNT(*) as news_count
            FROM chunks
            GROUP BY date
            ORDER BY date DESC
            LIMIT 7
            ''')
            
            recent_dates = cursor.fetchall()
            
            print(f"\n📅 Активность за последние 7 дней:")
            for date, count in recent_dates:
                print(f"   • {date}: {count} новостей")
            
            conn.close()
            
            print("✅ Базовый анализ трендов завершен")
            
        except Exception as e:
            print(f"⚠️  Ошибка анализа трендов: {e}")

def main():
    """Основная функция"""
    print("🚀 HR ANALYTICS DASHBOARD - СОЗДАНИЕ БАЗЫ ДАННЫХ")
    print("=" * 70)
    
    # Создаем .env если его нет
    if not os.path.exists('.env'):
        print("📝 Создание файла .env...")
        with open('.env', 'w', encoding='utf-8') as f:
            f.write("""# API ключи для HR Analytics Dashboard
GROQ_API_KEY=ваш_ключ_здесь
GIGACHAT_API_KEY=ваш_ключ_здесь

# Настройки
DEBUG=True
PORT=5000
""")
        print("✅ Файл .env создан")
        print("⚠️  ЗАПОЛНИТЕ API КЛЮЧ В ФАЙЛЕ .env ПЕРЕД ЗАПУСКОМ!")
        print("   Получите ключ на: https://console.groq.com/keys")
        return
    
    # Проверяем API ключ
    with open('.env', 'r') as f:
        content = f.read()
        if 'ваш_ключ_здесь' in content:
            print("❌ ВАЖНО: Заполните GROQ_API_KEY в файле .env!")
            print("   Без API ключа LLM не сможет проанализировать новости")
            return
    
    # Запускаем пайплайн
    pipeline = DataPipeline()
    pipeline.run_full_pipeline()

if __name__ == "__main__":
    main()
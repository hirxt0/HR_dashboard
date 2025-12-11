#!/usr/bin/env python
"""
Простой тест пайплайна
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db import Database
from app.orchestrator import PipelineOrchestrator

def test_database():
    print("🧪 Тестирование базы данных...")
    
    db = Database()
    
    # Проверяем методы
    stats = db.get_stats()
    print(f"✅ Статистика: {stats}")
    
    # Проверяем необработанные сообщения
    unprocessed = db.get_unprocessed_messages(limit=5)
    print(f"✅ Необработанных сообщений: {len(unprocessed)}")
    
    db.close()
    return True

def test_orchestrator():
    print("\n🧪 Тестирование оркестратора...")
    
    orchestrator = PipelineOrchestrator()
    
    # Тест 1: Статус
    status = orchestrator.get_current_status()
    print(f"✅ Статус получен")
    
    # Тест 2: Обработка сообщений (маленький батч)
    print("\n🤖 Тест обработки AI...")
    result = orchestrator.process_messages(batch_size=2)
    print(f"✅ Результат: {result}")
    
    # Тест 3: Анализ
    print("\n📊 Тест анализа...")
    analysis = orchestrator.analyze_data()
    print(f"✅ Найдено сигналов: {analysis.get('signals_count', 0)}")
    
    orchestrator.parser.close()
    orchestrator.db.close()
    return True

def add_test_data():
    """Добавляем тестовые данные если БД пустая"""
    print("\n📝 Добавление тестовых данных...")
    
    db = Database()
    
    # Проверяем, есть ли данные
    stats = db.get_stats()
    if stats['total_messages'] > 0:
        print(f"✅ В БД уже есть {stats['total_messages']} сообщений")
        return
    
    # Добавляем тестовые сообщения
    test_messages = [
        {
            "channel": "AI_News",
            "message_id": "test_1",
            "text": "Google представила новую AI модель Gemini. Производительность впечатляет!",
            "datetime": "2024-01-15T10:00:00",
            "permalink": "https://t.me/ai_news/1",
            "text_cleaned": "Google представила новую AI модель Gemini. Производительность впечатляет!",
            "channel_category": "технологии"
        },
        {
            "channel": "HR_Analytics",
            "message_id": "test_2",
            "text": "Рынок труда для AI специалистов растет. Зарплаты увеличились на 20%",
            "datetime": "2024-01-16T14:30:00",
            "permalink": "https://t.me/hr_analytics/2",
            "text_cleaned": "Рынок труда для AI специалистов растет. Зарплаты увеличились на 20%",
            "channel_category": "hr"
        },
        {
            "channel": "FinTech_Today",
            "message_id": "test_3",
            "text": "Банки внедряют AI для анализа рисков. Эффективность выросла на 30%",
            "datetime": "2024-01-17T09:15:00",
            "permalink": "https://t.me/fintech/3",
            "text_cleaned": "Банки внедряют AI для анализа рисков. Эффективность выросла на 30%",
            "channel_category": "финтех"
        }
    ]
    
    for msg in test_messages:
        msg_id = db.insert_message(msg)
        if msg_id:
            print(f"✅ Добавлено сообщение из {msg['channel']}")
    
    db.close()
    print("✅ Тестовые данные добавлены")

def main():
    print("=" * 50)
    print("ТЕСТ ПАЙПЛАЙНА HR ANALYTICS")
    print("=" * 50)
    
    try:
        # Добавляем тестовые данные если нужно
        add_test_data()
        
        # Тестируем БД
        if not test_database():
            print("❌ Тест базы данных не пройден")
            return
        
        # Тестируем оркестратор
        if not test_orchestrator():
            print("❌ Тест оркестратора не пройден")
            return
        
        print("\n" + "=" * 50)
        print("✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n❌ Ошибка тестирования: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
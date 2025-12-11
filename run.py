#!/usr/bin/env python
"""
Главный скрипт запуска HR Analytics Dashboard
"""
import sys
import os

# Добавляем текущую директорию в путь Python
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def main():
    """Точка входа в приложение"""
    print("""
    === HR ANALYTICS DASHBOARD ===
    
    Доступные команды:
    
    1. Запустить пайплайн (обработка + анализ)
    2. Добавить тестовые данные
    3. Только обработка AI
    4. Только анализ данных
    5. Запустить веб-интерфейс
    6. Показать статистику
    7. Быстрый старт (все шаги)
    0. Выход
    """)
    
    choice = input("\nВыберите действие (0-7): ").strip()
    
    if choice == "1":
        run_pipeline()
    elif choice == "2":
        add_test_data()
    elif choice == "3":
        process_ai()
    elif choice == "4":
        analyze_data()
    elif choice == "5":
        run_web_interface()
    elif choice == "6":
        show_stats()
    elif choice == "7":
        quick_start()
    elif choice == "0":
        print("Выход...")
        sys.exit(0)
    else:
        print("Неверный выбор")

def run_pipeline():
    """Запуск полного пайплайна"""
    print("\n🚀 Запуск полного пайплайна...")
    
    try:
        from app.orchestrator import PipelineOrchestrator
        
        orchestrator = PipelineOrchestrator()
        stats = orchestrator.run_full_pipeline()
        
        print(f"\n✅ Пайплайн завершен успешно!")
        print(f"📊 Статистика:")
        print(f"• Обработано AI: {stats.get('messages_processed', 0)}")
        print(f"• Найдено сигналов: {stats.get('signals_found', 0)}")
        
        # Закрываем БД
        orchestrator.db.close()
        
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

def add_test_data():
    """Добавление тестовых данных"""
    print("\n📝 Добавление тестовых данных...")
    
    try:
        from app.db import Database
        
        db = Database()
        
        # Проверяем текущую статистику
        stats = db.get_stats()
        print(f"📊 Текущая статистика:")
        print(f"• Сообщений: {stats['total_messages']}")
        
        if stats['total_messages'] > 0:
            response = input("В базе уже есть данные. Добавить еще? (y/n): ").strip().lower()
            if response != 'y':
                db.close()
                return
        
        # Добавляем тестовые сообщения
        test_messages = [
            {
                "channel": "AI_News",
                "message_id": "test_001",
                "text": "Искусственный интеллект революционизирует HR: автоматизация найма повышает эффективность на 40%",
                "datetime": "2024-01-15T10:00:00",
                "permalink": "https://t.me/ai_news/1",
                "text_cleaned": "Искусственный интеллект революционизирует HR: автоматизация найма повышает эффективность на 40%",
                "channel_category": "технологии"
            },
            {
                "channel": "HR_Analytics",
                "message_id": "test_002",
                "text": "Рынок труда для AI-специалистов: спрос растет, но зарплаты снижаются из-за увеличения предложения",
                "datetime": "2024-01-16T14:30:00",
                "permalink": "https://t.me/hr_analytics/2",
                "text_cleaned": "Рынок труда для AI-специалистов: спрос растет, но зарплаты снижаются из-за увеличения предложения",
                "channel_category": "hr"
            },
            {
                "channel": "FinTech_Today",
                "message_id": "test_003",
                "text": "Банки активно внедряют AI для анализа кредитных рисков. Результаты впечатляют: снижение дефолтов на 25%",
                "datetime": "2024-01-17T09:15:00",
                "permalink": "https://t.me/fintech/3",
                "text_cleaned": "Банки активно внедряют AI для анализа кредитных рисков. Результаты впечатляют: снижение дефолтов на 25%",
                "channel_category": "финтех"
            },
            {
                "channel": "Startup_News",
                "message_id": "test_004",
                "text": "Стартап в области HR-tech привлек $10 млн инвестиций. Платформа использует AI для подбора кандидатов",
                "datetime": "2024-01-18T11:45:00",
                "permalink": "https://t.me/startup/4",
                "text_cleaned": "Стартап в области HR-tech привлек $10 млн инвестиций. Платформа использует AI для подбора кандидатов",
                "channel_category": "бизнес"
            },
            {
                "channel": "Edu_Tech",
                "message_id": "test_005",
                "text": "Университеты внедряют курсы по AI для HR-специалистов. Обучение фокусируется на практическом применении технологий",
                "datetime": "2024-01-19T16:20:00",
                "permalink": "https://t.me/edu/5",
                "text_cleaned": "Университеты внедряют курсы по AI для HR-специалистов. Обучение фокусируется на практическом применении технологий",
                "channel_category": "образование"
            }
        ]
        
        added_count = 0
        for msg in test_messages:
            msg_id = db.insert_message(msg)
            if msg_id:
                added_count += 1
        
        print(f"\n✅ Добавлено {added_count} тестовых сообщений")
        
        # Показываем обновленную статистику
        stats = db.get_stats()
        print(f"\n📊 Новая статистика:")
        print(f"• Всего сообщений: {stats['total_messages']}")
        print(f"• Обработано: {stats['processed_messages']}")
        print(f"• Ожидает обработки: {stats['unprocessed_messages']}")
        
        db.close()
        
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")

def process_ai():
    """Обработка сообщений через AI"""
    print("\n🤖 Обработка сообщений AI...")
    
    try:
        from app.orchestrator import PipelineOrchestrator
        
        batch_size = input("Размер батча (по умолчанию 5): ").strip()
        batch_size = int(batch_size) if batch_size.isdigit() else 5
        
        orchestrator = PipelineOrchestrator()
        stats = orchestrator.process_messages(batch_size)
        
        print(f"\n✅ Обработано {stats.get('processed', 0)} сообщений")
        print(f"Использован AI: {'Да' if stats.get('ai_used', False) else 'Нет (заглушка)'}")
        
        if stats.get("errors"):
            print(f"⚠️ Ошибок: {len(stats['errors'])}")
            for error in stats.get("error_samples", [])[:2]:
                print(f"  • {error}")
        
        orchestrator.db.close()
        
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")

def analyze_data():
    """Анализ данных"""
    print("\n📊 Анализ данных и поиск сигналов...")
    
    try:
        from app.orchestrator import PipelineOrchestrator
        
        orchestrator = PipelineOrchestrator()
        stats = orchestrator.analyze_data()
        
        print(f"\n✅ Найдено {stats.get('signals_count', 0)} сигналов")
        
        if stats.get("signals"):
            print("\n🎯 Активные сигналы:")
            for signal in stats["signals"][:5]:
                print(f"• {signal['tag']}: {signal['signal']} ({signal['count']} упоминаний)")
        else:
            print("\nℹ️ Нет активных сигналов")
        
        orchestrator.db.close()
        
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")

def run_web_interface():
    """Запуск веб-интерфейса"""
    print("\n🌐 Запуск веб-интерфейса...")
    print("Сервер будет доступен по адресу: http://localhost:8000")
    print("Нажмите Ctrl+C для остановки")
    
    import subprocess
    import sys
    
    try:
        subprocess.run([sys.executable, "-m", "uvicorn", "app.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"])
    except KeyboardInterrupt:
        print("\nСервер остановлен")
    except Exception as e:
        print(f"\n❌ Ошибка запуска: {e}")

def show_stats():
    """Показать статистику"""
    print("\n📊 Статистика системы...")
    
    try:
        from app.db import Database
        
        db = Database()
        stats = db.get_stats()
        
        print(f"\n📁 База данных:")
        print(f"• Всего сообщений: {stats['total_messages']}")
        print(f"• Обработано: {stats['processed_messages']}")
        print(f"• Ожидает обработки: {stats['unprocessed_messages']}")
        print(f"• Каналов: {stats['channels_count']}")
        
        if stats['channels']:
            print(f"\n📡 Топ каналов:")
            for channel in stats['channels'][:5]:
                print(f"  • {channel['channel']}: {channel['count']}")
        
        # Проверяем AI доступность
        try:
            from app.processor import Processor
            processor = Processor()
            print(f"\n🤖 AI процессор: Доступен")
        except:
            print(f"\n🤖 AI процессор: Недоступен (используются заглушки)")
        
        db.close()
        
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")

def quick_start():
    """Быстрый старт всей системы"""
    print("\n⚡ БЫСТРЫЙ СТАРТ СИСТЕМЫ")
    print("=" * 40)
    
    try:
        from app.db import Database
        
        # Шаг 1: Проверяем базу данных
        print("\n1. Проверка базы данных...")
        db = Database()
        stats = db.get_stats()
        
        if stats['total_messages'] == 0:
            print("   ⚠️ База пустая. Добавляю тестовые данные...")
            # Добавляем минимум данных
            test_msg = {
                "channel": "Test_Channel",
                "message_id": "quick_001",
                "text": "AI в HR: автоматизация рекрутинга показывает рост эффективности на 35%",
                "datetime": "2024-01-20T10:00:00",
                "permalink": "https://t.me/test/1",
                "text_cleaned": "AI в HR: автоматизация рекрутинга показывает рост эффективности на 35%",
                "channel_category": "технологии"
            }
            db.insert_message(test_msg)
            print("   ✅ Добавлено тестовое сообщение")
        
        db.close()
        
        # Шаг 2: Обработка
        print("\n2. Обработка AI...")
        from app.orchestrator import PipelineOrchestrator
        orchestrator = PipelineOrchestrator()
        process_stats = orchestrator.process_messages(batch_size=3)
        print(f"   ✅ Обработано: {process_stats.get('processed', 0)} сообщений")
        
        # Шаг 3: Анализ
        print("\n3. Анализ данных...")
        analysis_stats = orchestrator.analyze_data()
        print(f"   ✅ Найдено сигналов: {analysis_stats.get('signals_count', 0)}")
        
        if analysis_stats.get("signals"):
            print("\n   🎯 Обнаруженные сигналы:")
            for signal in analysis_stats["signals"]:
                print(f"   • {signal['tag']}: {signal['signal']}")
        
        orchestrator.db.close()
        
        # Шаг 4: Запуск веб-интерфейса
        print("\n4. Запуск веб-интерфейса...")
        print("   Сервер будет доступен по: http://localhost:8000")
        print("   Нажмите Ctrl+C в новом окне для остановки")
        
        import threading
        import time
        
        def start_server():
            import subprocess
            import sys
            subprocess.run([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"])
        
        # Запускаем сервер в отдельном потоке
        server_thread = threading.Thread(target=start_server, daemon=True)
        server_thread.start()
        
        print("\n✅ Система запущена! Веб-интерфейс доступен.")
        print("   Для остановки нажмите Ctrl+C")
        
        # Ожидаем
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nСистема остановлена")
        
    except Exception as e:
        print(f"\n❌ Ошибка быстрого старта: {e}")

if __name__ == "__main__":
    main()
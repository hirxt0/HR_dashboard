import time
import logging
import random
from datetime import datetime
from typing import Dict, List
import os

# Наши модули
from app.db import Database
from app.aggregator import Aggregator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class PipelineOrchestrator:
    def __init__(self):
        self.db = Database()
        self.aggregator = Aggregator()
        
        # Пытаемся импортировать процессор (может быть недоступен)
        try:
            from app.processor import Processor
            self.processor = Processor()
            self.ai_available = True
            logger.info("✅ AI процессор загружен")
        except Exception as e:
            self.processor = None
            self.ai_available = False
            logger.warning(f"⚠️ AI процессор недоступен: {e}")
        
        # Статистика
        self.stats = {
            "messages_processed": 0,
            "signals_found": 0,
            "last_run": None,
            "ai_available": self.ai_available
        }
    
    def run_full_pipeline(self):
        """Запуск полного пайплайна: обработка → анализ"""
        logger.info("🚀 Запуск пайплайна...")
        
        try:
            # Шаг 1: Обработка AI
            logger.info("🤖 Шаг 1: Обработка сообщений AI...")
            processing_stats = self.process_messages(batch_size=10)
            
            # Шаг 2: Анализ и сигналы
            logger.info("📊 Шаг 2: Анализ данных и поиск сигналов...")
            analysis_stats = self.analyze_data()
            
            # Обновляем статистику
            self.stats.update({
                "messages_processed": processing_stats.get("processed", 0),
                "signals_found": analysis_stats.get("signals_count", 0),
                "last_run": datetime.now().isoformat()
            })
            
            # Шаг 3: Отчет
            logger.info("📋 Шаг 3: Генерация отчета...")
            self.generate_report()
            
            logger.info("✅ Пайплайн успешно завершен!")
            
            return self.stats
            
        except Exception as e:
            logger.error(f"❌ Ошибка в пайплайне: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def process_messages(self, batch_size: int = 10) -> Dict:
        """Обработка сообщений через AI или заглушку"""
        try:
            # Получаем необработанные сообщения
            unprocessed = self.db.get_unprocessed_messages(limit=batch_size)
            logger.info(f"Найдено {len(unprocessed)} необработанных сообщений")
            
            if not unprocessed:
                logger.info("Нет необработанных сообщений")
                return {"processed": 0, "message": "Нет необработанных сообщений"}
            
            processed_count = 0
            errors = []
            
            for msg in unprocessed:
                try:
                    logger.info(f"Обработка сообщения {msg.get('id')} из {msg.get('channel')}")
                    
                    # Проверяем доступность AI
                    if self.ai_available and self.processor:
                        # Обрабатываем через AI
                        meta = self.processor.process_message(msg)
                        logger.info(f"✅ AI обработка: {meta.get('tags', [])} | {meta.get('sentiment')}")
                    else:
                        # Используем заглушку
                        meta = self._create_fallback_metadata(msg)
                        logger.info(f"✅ Заглушка: {meta.get('tags', [])} | {meta.get('sentiment')}")
                    
                    # Сохраняем метаданные
                    self.db.insert_metadata(msg["id"], meta)
                    processed_count += 1
                    
                except Exception as e:
                    error_msg = f"Ошибка обработки сообщения {msg.get('id')}: {str(e)[:100]}"
                    errors.append(error_msg)
                    logger.warning(error_msg)
            
            stats = {
                "processed": processed_count,
                "errors": len(errors),
                "error_samples": errors[:3] if errors else [],
                "batch_size": batch_size,
                "ai_used": self.ai_available
            }
            
            logger.info(f"✅ Обработано {processed_count} сообщений")
            return stats
            
        except Exception as e:
            logger.error(f"Ошибка обработки: {e}")
            import traceback
            traceback.print_exc()
            return {"processed": 0, "error": str(e)}
    
    def _create_fallback_metadata(self, msg: Dict) -> Dict:
        """Создание заглушки метаданных если GigaChat недоступен"""
        text = msg.get("text_cleaned", msg.get("text", "")).lower()
        category = msg.get("channel_category", "").lower()
        
        # Теги на основе категории и текста
        tags = []
        
        # Определяем теги по категории
        if "техн" in category or any(word in text for word in ["ии", "ai", "нейросеть", "машинн", "технолог"]):
            tags.extend(["ИИ", "Технологии"])
        if "hr" in category or any(word in text for word in ["hr", "кадр", "работ", "труд", "сотрудник"]):
            tags.extend(["HR", "Рынок труда"])
        if "финт" in category or any(word in text for word in ["финтех", "банк", "деньг", "инвест", "финанс"]):
            tags.extend(["Финтех", "Финансы"])
        if "образ" in category or any(word in text for word in ["образован", "универ", "курс", "обучен", "студент"]):
            tags.extend(["Образование"])
        if "бизн" in category or any(word in text for word in ["стартап", "бизнес", "компан", "предпри"]):
            tags.extend(["Бизнес", "Стартапы"])
        
        # Если не нашли тегов, используем общий
        if not tags:
            tags = ["Общее"]
        
        # Определяем тональность
        positive_words = ["прорыв", "рост", "успех", "улучш", "эффектив", "новый", "развит"]
        negative_words = ["проблем", "сложн", "риск", "сокращ", "увольн", "падение", "кризис"]
        
        sentiment_score = 0
        positive_count = sum(1 for word in positive_words if word in text)
        negative_count = sum(1 for word in negative_words if word in text)
        
        if positive_count > negative_count:
            sentiment = "positive"
            sentiment_score = random.uniform(0.1, 1.0)
        elif negative_count > positive_count:
            sentiment = "negative"
            sentiment_score = random.uniform(-1.0, -0.1)
        else:
            sentiment = "neutral"
            sentiment_score = random.uniform(-0.1, 0.1)
        
        # Определяем инсайдера
        insider_keywords = ["источник", "инсайдер", "эксклюзив", "слив", "внутренний"]
        is_insider = any(keyword in text for keyword in insider_keywords) or random.random() < 0.2
        
        return {
            "tags": list(set(tags)),  # Убираем дубли
            "sentiment": sentiment,
            "sentiment_score": sentiment_score,
            "is_insider": is_insider,
            "insider_confidence": random.uniform(0.3, 0.9) if is_insider else random.uniform(0, 0.3)
        }
    
    def analyze_data(self) -> Dict:
        """Анализ данных и поиск сигналов"""
        try:
            # Получаем все обработанные сообщения
            all_data = self.db.get_all_metadata()
            
            if not all_data:
                logger.warning("Нет данных для анализа")
                return {"signals_count": 0, "signals": []}
            
            logger.info(f"📊 Анализ {len(all_data)} документов...")
            
            # Запускаем агрегатор
            signals = self.aggregator.compute_signals(all_data)
            
            # Фильтруем только активные сигналы
            active_signals = [s for s in signals if s["signal"] != "none"]
            
            stats = {
                "total_documents": len(all_data),
                "signals_count": len(active_signals),
                "signals": active_signals[:10]  # Ограничиваем для отчета
            }
            
            logger.info(f"📈 Найдено {len(active_signals)} активных сигналов")
            
            # Логируем найденные сигналы
            for signal in active_signals[:5]:
                logger.info(f"  • {signal['tag']}: {signal['signal']} ({signal['count']} упоминаний)")
            
            return stats
            
        except Exception as e:
            logger.error(f"Ошибка анализа: {e}")
            import traceback
            traceback.print_exc()
            return {"signals_count": 0, "error": str(e)}
    
    def generate_report(self):
        """Генерация отчета о работе"""
        try:
            report_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            report = f"""
=== ОТЧЕТ О РАБОТЕ ПАЙПЛАЙНА ===
Время: {report_time}
AI доступен: {'Да' if self.ai_available else 'Нет'}

📊 СТАТИСТИКА:
• Обработано сообщений: {self.stats['messages_processed']}
• Найдено сигналов: {self.stats['signals_found']}

🎯 АКТИВНЫЕ СИГНАЛЫ:
"""
            
            # Получаем текущие сигналы для отчета
            all_data = self.db.get_all_metadata()
            if all_data:
                signals = self.aggregator.compute_signals(all_data)
                active_signals = [s for s in signals if s["signal"] != "none"]
                
                if active_signals:
                    for signal in active_signals[:5]:
                        report += f"• {signal['tag']}: {signal['signal']} ({signal['count']} упоминаний)\n"
                else:
                    report += "Нет активных сигналов\n"
            
            report += "\n✅ Пайплайн выполнен успешно"
            
            # Сохраняем отчет в файл
            os.makedirs("logs", exist_ok=True)
            
            filename = f"logs/report_{datetime.now().strftime('%Y%m%d_%H%M')}.txt"
            with open(filename, "w", encoding="utf-8") as f:
                f.write(report)
            
            logger.info(f"📄 Отчет сохранен в {filename}")
            print(report)
            
        except Exception as e:
            logger.error(f"Ошибка генерации отчета: {e}")
            import traceback
            traceback.print_exc()
    
    def get_current_status(self) -> Dict:
        """Текущий статус пайплайна"""
        db_stats = self.db.get_stats()
        
        return {
            "stats": self.stats,
            "database": db_stats,
            "timestamp": datetime.now().isoformat()
        }

def simple_main():
    """Упрощенная точка входа"""
    print("""
    🤖 HR ANALYTICS - Упрощенный пайплайн
    =====================================
    1. Обработка сообщений AI/заглушкой
    2. Анализ данных и поиск сигналов
    3. Показать статистику
    4. Создать тестовые данные
    0. Выход
    """)
    
    orchestrator = PipelineOrchestrator()
    
    while True:
        choice = input("\nВыберите действие (0-4): ").strip()
        
        if choice == "1":
            print("Обработка сообщений...")
            batch_size = input("Сколько сообщений обработать? (по умолчанию 10): ").strip()
            batch_size = int(batch_size) if batch_size.isdigit() else 10
            
            stats = orchestrator.process_messages(batch_size)
            print(f"\n✅ Обработано {stats.get('processed', 0)} сообщений")
            print(f"Использован AI: {'Да' if stats.get('ai_used') else 'Нет (заглушка)'}")
            
        elif choice == "2":
            print("Анализ данных...")
            stats = orchestrator.analyze_data()
            print(f"\n✅ Найдено {stats.get('signals_count', 0)} сигналов")
            
            if stats.get("signals"):
                print("\n🎯 Активные сигналы:")
                for signal in stats["signals"][:5]:
                    print(f"• {signal['tag']}: {signal['signal']} ({signal['count']} упом.)")
            
        elif choice == "3":
            status = orchestrator.get_current_status()
            print(f"\n📊 Текущий статус:")
            print(f"• Всего сообщений: {status['database'].get('total_messages', 0)}")
            print(f"• Обработано: {status['database'].get('processed_messages', 0)}")
            print(f"• Ожидает: {status['database'].get('unprocessed_messages', 0)}")
            print(f"• AI доступен: {'Да' if orchestrator.ai_available else 'Нет'}")
            print(f"• Последний запуск: {status['stats'].get('last_run', 'никогда')}")
            
        elif choice == "4":
            print("Создание тестовых данных...")
            from app.db import Database
            db = Database()
            
            # Добавляем 5 тестовых сообщений
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
            
            added = 0
            for msg in test_messages:
                msg_id = db.insert_message(msg)
                if msg_id:
                    added += 1
            
            print(f"✅ Добавлено {added} тестовых сообщений")
            db.close()
            
        elif choice == "0":
            print("Выход...")
            orchestrator.db.close()
            break
            
        else:
            print("Неверный выбор")

if __name__ == "__main__":
    simple_main()
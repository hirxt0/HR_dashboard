from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import asyncio
import threading
from datetime import datetime

from app.db import Database
from app.processor import Processor
from app.aggregator import Aggregator
from app.orchestrator import PipelineOrchestrator  # Новый модуль

app = FastAPI(title="HR Analytics Dashboard", version="1.0")
db = Database()
processor = Processor()
aggregator = Aggregator()
orchestrator = PipelineOrchestrator()

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# Флаг для отслеживания работы пайплайна
pipeline_running = False
pipeline_status = {
    "running": False,
    "last_run": None,
    "stats": {}
}

@app.get("/", response_class=HTMLResponse)
def index(req: Request):
    """Главная страница дашборда"""
    docs = db.get_all_metadata()
    signals = aggregator.compute_signals(docs)
    
    # Статистика для дашборда
    stats = db.get_stats()
    
    return templates.TemplateResponse("index.html", {
        "request": req,
        "signals": signals,
        "stats": stats,
        "pipeline_status": pipeline_status
    })

@app.get("/api/search")
def search(q: str):
    """Поиск по тегам"""
    tags = [tag.strip() for tag in q.split(",") if tag.strip()]
    docs = db.get_by_tags(tags)
    return docs[:20]  # Ограничиваем результат

@app.post("/api/process_message")
def process_message(msg: dict):
    """Обработка одного сообщения через AI"""
    try:
        meta = processor.process_message(msg)
        return {"success": True, "metadata": meta}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/stats")
def get_stats():
    """Получение статистики"""
    stats = db.get_stats()
    docs = db.get_all_metadata()
    signals = aggregator.compute_signals(docs)
    
    return {
        "database": stats,
        "signals_count": len([s for s in signals if s["signal"] != "none"]),
        "pipeline": pipeline_status,
        "timestamp": datetime.now().isoformat()
    }

@app.post("/api/pipeline/run")
def run_pipeline(background_tasks: BackgroundTasks):
    """Запуск пайплайна в фоновом режиме"""
    global pipeline_running
    
    if pipeline_running:
        return {"success": False, "error": "Пайплайн уже выполняется"}
    
    pipeline_running = True
    
    def pipeline_task():
        global pipeline_running, pipeline_status
        try:
            stats = orchestrator.run_full_pipeline()
            pipeline_status = {
                "running": False,
                "last_run": datetime.now().isoformat(),
                "stats": stats,
                "success": True
            }
        except Exception as e:
            pipeline_status = {
                "running": False,
                "last_run": datetime.now().isoformat(),
                "error": str(e),
                "success": False
            }
        finally:
            pipeline_running = False
    
    # Запуск в фоновом потоке
    thread = threading.Thread(target=pipeline_task)
    thread.start()
    
    return {
        "success": True,
        "message": "Пайплайн запущен в фоновом режиме",
        "job_id": "pipeline_" + datetime.now().strftime("%Y%m%d_%H%M%S")
    }

@app.get("/api/pipeline/status")
def get_pipeline_status():
    """Статус пайплайна"""
    return {
        "running": pipeline_running,
        "status": pipeline_status
    }

@app.get("/api/messages/recent")
def get_recent_messages(limit: int = 10):
    """Получение последних сообщений"""
    cursor = db.conn.cursor()
    cursor.execute('''
    SELECT m.*, mm.tags, mm.sentiment 
    FROM messages m
    LEFT JOIN metadata mm ON m.id = mm.message_id
    ORDER BY m.datetime DESC
    LIMIT ?
    ''', (limit,))
    
    return [dict(row) for row in cursor.fetchall()]

@app.get("/admin")
def admin_panel(req: Request):
    """Панель администратора для управления пайплайном"""
    return templates.TemplateResponse("admin.html", {
        "request": req,
        "pipeline_status": pipeline_status,
        "stats": db.get_stats()
    })

# Запуск пайплайна по расписанию (если нужно)
def start_scheduled_pipeline():
    """Запуск пайплайна по расписанию"""
    import schedule
    import time
    
    def job():
        print(f"[{datetime.now()}] Запуск запланированного пайплайна...")
        orchestrator.run_full_pipeline()
    
    # Запускать каждый час
    schedule.every().hour.do(job)
    
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    import uvicorn
    
    print("""
    === HR ANALYTICS DASHBOARD ===
    1. Запустить веб-интерфейс
    2. Запустить полный пайплайн один раз
    3. Запустить сбор данных
    4. Запустить фоновый пайплайн по расписанию
    """)
    
    choice = input("Выберите действие: ").strip()
    
    if choice == "1":
        # Запуск веб-сервера
        uvicorn.run(app, host="0.0.0.0", port=8000)
        
    elif choice == "2":
        # Однократный запуск пайплайна
        orchestrator.run_full_pipeline()
        
    elif choice == "3":
        # Только сбор данных
        stats = orchestrator.collect_data()
        print(f"✅ Собрано {stats.get('new_messages', 0)} сообщений")
        
    elif choice == "4":
        # Фоновый пайплайн по расписанию
        # В отдельном потоке запускаем планировщик
        import threading
        scheduler_thread = threading.Thread(target=start_scheduled_pipeline, daemon=True)
        scheduler_thread.start()
        
        # И одновременно запускаем веб-интерфейс
        print("Фоновый пайплайн запущен. Веб-интерфейс доступен по http://localhost:8000")
        uvicorn.run(app, host="0.0.0.0", port=8000)
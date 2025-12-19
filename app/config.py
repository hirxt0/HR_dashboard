"""
config.py - Конфигурация приложения
"""
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # API ключи
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "ваш_ключ_здесь")
    GIGACHAT_API_KEY = os.getenv("GIGACHAT_API_KEY", "ваш_ключ_здесь")
    
    # Настройки базы данных
    DATABASE_PATH = "telegram_data.db"
    
    # Настройки парсера
    TELEGRAM_CHANNELS = [
        "https://t.me/KarpovCourses",
        "https://t.me/naumenprojectruler",
        "https://t.me/scientific_opensource",
        "https://t.me/itmo_opensource",
        "https://t.me/TheDataEconomy",
        "https://t.me/machinelearning_ru",
        "https://t.me/minobrnaukiofficial",
        "https://t.me/sciencenewsru",
        "https://t.me/technewstel",
        "https://t.me/ainewsru"
    ]
    
    # Настройки LLM
    GROQ_MODEL = "llama-3.3-70b-versatile"
    GIGACHAT_MODEL = "GigaChat"
    
    # Настройки анализа
    TREND_DAYS_BACK = 30
    MIN_MENTIONS_FOR_SIGNAL = 5
    
    # Настройки Flask
    DEBUG = os.getenv("DEBUG", "True").lower() == "true"
    PORT = int(os.getenv("PORT", 5000))
    
    # Пути
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    STATIC_DIR = os.path.join(BASE_DIR, "static")
    TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
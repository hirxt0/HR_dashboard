import os
from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.getenv("DB_PATH", "telegram_data.db")
GIGACHAT_API_URL = os.getenv("GIGACHAT_API_URL")
GIGACHAT_API_KEY = os.getenv("GIGACHAT_API_KEY")

TAGS_TAXONOMY_PATH = os.getenv("TAGS_TAXONOMY_PATH", "taxonomy/tags.csv")

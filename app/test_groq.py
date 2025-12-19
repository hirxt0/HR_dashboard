import requests
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GROQ_API_KEY")

print(f"🔑 API ключ: {'***' + api_key[-4:] if api_key else 'Не найден'}")

url = "https://api.groq.com/openai/v1/chat/completions"

headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

data = {
    "model": "llama-3.3-70b-versatile",
    "messages": [{"role": "user", "content": "Привет! Ответь 'тест пройден'."}],
    "temperature": 0.3,
    "max_tokens": 10
}

response = requests.post(url, headers=headers, json=data, timeout=10)
print(f"📡 Ответ API: HTTP {response.status_code}")
print(f"📄 Тело ответа: {response.text[:200]}")
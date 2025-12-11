#!/usr/bin/env python
"""
Полное тестирование GigaChat API
"""
import os
import sys
import requests
import base64
from dotenv import load_dotenv

# Добавляем путь для импорта
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

API_KEY = os.getenv("GIGACHAT_API_KEY")
print(f"🔑 API Key: {API_KEY[:20]}...")

if not API_KEY:
    print("❌ API ключ не найден!")
    exit(1)

def test_oauth_token():
    """Тест получения OAuth токена"""
    print("\n1. Тестируем получение OAuth токена...")
    
    if ':' not in API_KEY:
        print("⚠️ Ключ не в формате client_id:client_secret")
        return None
    
    client_id, client_secret = API_KEY.split(':', 1)
    
    # Кодируем для Basic Auth
    credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    
    token_url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
    
    headers = {
        "Authorization": f"Basic {credentials}",
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json"
    }
    
    data = {
        "scope": "GIGACHAT_API_PERS"
    }
    
    try:
        # Отключаем проверку SSL для тестирования
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        response = requests.post(
            token_url,
            headers=headers,
            data=data,
            verify=False,
            timeout=10
        )
        
        print(f"Статус: {response.status_code}")
        
        if response.status_code == 200:
            token_data = response.json()
            access_token = token_data.get("access_token")
            expires_in = token_data.get("expires_in", 1800)
            print(f"✅ Токен получен! Действителен {expires_in} секунд")
            print(f"Токен: {access_token[:50]}...")
            return access_token
        else:
            print(f"❌ Ошибка: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Исключение: {e}")
        return None

def test_chat_api(access_token):
    """Тест Chat Completions API"""
    print("\n2. Тестируем Chat API...")
    
    api_url = "https://api.gigachat.ai/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "GigaChat",
        "messages": [
            {
                "role": "user",
                "content": "Привет! Ответь одним словом: 'Работает'"
            }
        ],
        "temperature": 0.1,
        "max_tokens": 10
    }
    
    try:
        response = requests.post(
            api_url,
            headers=headers,
            json=payload,
            timeout=10
        )
        
        print(f"Статус: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            answer = data["choices"][0]["message"]["content"]
            print(f"✅ Успех! Ответ: {answer}")
            return True
        else:
            print(f"❌ Ошибка: {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"❌ Исключение: {e}")
        return False

def test_direct_with_key():
    """Прямой тест с ключом"""
    print("\n3. Прямой тест с API ключом...")
    
    api_url = "https://api.gigachat.ai/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "GigaChat",
        "messages": [
            {
                "role": "user",
                "content": "Тест"
            }
        ],
        "temperature": 0.1,
        "max_tokens": 10
    }
    
    try:
        response = requests.post(
            api_url,
            headers=headers,
            json=payload,
            timeout=10
        )
        
        print(f"Статус: {response.status_code}")
        print(f"Ответ: {response.text[:200]}")
        
        return response.status_code == 200
        
    except Exception as e:
        print(f"❌ Исключение: {e}")
        return False

def main():
    print("🔍 ПОЛНОЕ ТЕСТИРОВАНИЕ GIGACHAT API")
    print("=" * 50)
    
    # Тест 1: Прямой доступ с ключом
    if test_direct_with_key():
        print("\n🎉 Прямой доступ работает! Используйте ключ как access token.")
        return
    
    # Тест 2: OAuth + Chat API
    access_token = test_oauth_token()
    if access_token:
        if test_chat_api(access_token):
            print("\n🎉 OAuth + Chat API работают!")
            print(f"\n💡 Обновите .env файл:")
            print(f'GIGACHAT_API_KEY="{access_token}"')
        else:
            print("\n❌ Chat API не работает с полученным токеном")
    else:
        print("\n❌ Не удалось получить access token")

if __name__ == "__main__":
    main()
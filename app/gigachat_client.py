import requests
import json
import time
import base64
from app.config import GIGACHAT_API_URL, GIGACHAT_API_KEY

class GigaChatClient:
    def __init__(self):
        self.api_url = GIGACHAT_API_URL
        self.api_key = GIGACHAT_API_KEY
        self.access_token = None
        self.token_expires = 0
        
        if not self.api_url or not self.api_key:
            print("⚠️ Внимание: GigaChat API не настроен.")
            raise RuntimeError("GigaChat credentials missing")
        
        print(f"✅ GigaChat клиент инициализирован")
        print(f"   API URL: {self.api_url}")
        self._get_access_token()
    
    def _get_access_token(self):
        """Получение access token через OAuth"""
        try:
            # Проверяем формат ключа
            if ':' in self.api_key:
                # Это client_id:client_secret
                client_id, client_secret = self.api_key.split(':', 1)
                
                # Кодируем в base64 для Basic Auth
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
                
                response = requests.post(
                    token_url,
                    headers=headers,
                    data=data,
                    verify=False,  # Может потребоваться для самоподписанных сертификатов
                    timeout=10
                )
                
                if response.status_code == 200:
                    token_data = response.json()
                    self.access_token = token_data.get("access_token")
                    # Токен обычно действителен 30 минут
                    self.token_expires = time.time() + 1800
                    print("✅ Access token получен")
                else:
                    print(f"❌ Ошибка получения токена: {response.status_code}")
                    print(f"Ответ: {response.text}")
                    raise Exception(f"Token error: {response.status_code}")
            else:
                # Предполагаем, что это уже access token
                self.access_token = self.api_key
                print("✅ Используется предоставленный access token")
                
        except Exception as e:
            print(f"❌ Ошибка получения access token: {e}")
            raise
    
    def _check_token(self):
        """Проверяем и обновляем token если нужно"""
        if not self.access_token or time.time() > self.token_expires - 60:
            self._get_access_token()
    
    def classify_chunk(self, text: str, allowed_tags: list[str]):
        self._check_token()
        
        prompt = f"""
        Ты - аналитик HR и бизнес-новостей. Проанализируй текст новости:

        ТЕКСТ: {text}

        ВЫБЕРИ подходящие теги ТОЛЬКО из этого списка (максимум 3 тега):
        {', '.join(allowed_tags)}

        ОПРЕДЕЛИ тональность: positive, negative или neutral.

        ОЦЕНИ вероятность что это инсайдерская информация.

        Верни ответ в формате JSON:
        {{
          "tags": ["тег1", "тег2"],
          "sentiment": "positive/negative/neutral",
          "sentiment_score": число от -1 до 1,
          "is_insider": true/false,
          "insider_confidence": число от 0 до 1
        }}
        """
        
        try:
            response = requests.post(
                self.api_url,
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "GigaChat",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                    "max_tokens": 500
                },
                timeout=30
            )
            
            print(f"Статус ответа GigaChat: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                raw_response = data["choices"][0]["message"]["content"]
                
                # Очищаем ответ
                raw_response = raw_response.strip()
                if raw_response.startswith("```json"):
                    raw_response = raw_response[7:]
                if raw_response.endswith("```"):
                    raw_response = raw_response[:-3]
                
                result = json.loads(raw_response)
                
                # Валидация
                required_fields = ["tags", "sentiment", "sentiment_score", "is_insider", "insider_confidence"]
                for field in required_fields:
                    if field not in result:
                        result[field] = [] if field == "tags" else "" if field == "sentiment" else 0.0
                
                return result
            else:
                print(f"❌ Ошибка API: {response.status_code}")
                print(f"Ответ: {response.text[:200]}")
                raise Exception(f"API error: {response.status_code}")
                
        except json.JSONDecodeError as e:
            print(f"❌ Ошибка парсинга JSON: {e}")
            print(f"Сырой ответ: {raw_response[:200]}")
            raise
        except Exception as e:
            print(f"❌ Ошибка GigaChat: {e}")
            raise
    
    def test_connection(self):
        """Тестирование подключения"""
        try:
            self._check_token()
            print("✅ Token доступен")
            
            # Простой тестовый запрос
            test_prompt = "Привет! Ответь 'OK'"
            
            response = requests.post(
                self.api_url,
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "GigaChat",
                    "messages": [{"role": "user", "content": test_prompt}],
                    "temperature": 0.1,
                    "max_tokens": 10
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                answer = data["choices"][0]["message"]["content"]
                print(f"✅ Тестовый запрос успешен: {answer}")
                return True
            else:
                print(f"❌ Тестовый запрос неудачен: {response.status_code}")
                print(f"Ответ: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Ошибка тестирования: {e}")
            return False
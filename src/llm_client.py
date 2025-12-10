import os
import random
from typing import List, Dict

class LLMClient:
    def __init__(self, mode="mock", provider="gigachat", api_key=None, endpoint=None):
        self.mode = mode
        self.provider = provider
        
        # Берем API ключ из аргумента, или из .env, или из переменных окружения системы
        self.api_key = api_key or os.getenv("GIGACHAT_API_KEY") or os.getenv("API_KEY")
        
        # Берем endpoint из аргумента, или из .env, или используем дефолтный
        self.endpoint = endpoint or os.getenv("GIGACHAT_ENDPOINT") or "https://gigachat.devices.sberbank.ru/api/v1"
        
        if self.mode == "real" and not self.api_key:
            print("Warning: Running in real mode without API key. Set GIGACHAT_API_KEY in .env file")

    def generate(self, prompt: str, system_prompt: str = "", max_tokens: int = 256) -> str:
        """
        Single text generation.
        For real mode: implement API call to GigaChat here.
        """
        if self.mode == "mock":
            return self._mock_generate(prompt, system_prompt)
        else:
            return self._real_generate(prompt, system_prompt, max_tokens)

    def generate_batch(self, prompts: List[str], system_prompt: str = "", max_tokens: int = 256) -> List[str]:
        if self.mode == "mock":
            return [self._mock_generate(p, system_prompt) for p in prompts]
        else:
            return [self._real_generate(p, system_prompt, max_tokens) for p in prompts]

    def _mock_generate(self, prompt: str, system_prompt: str) -> str:
        # Очень простая имитация: ищем ключевые слова, возвращаем короткий ответ.
        low = prompt.lower()
        if "назови тему" in prompt or "дай название" in prompt:
            # вернём короткое ёмкое название
            words = low.split()
            # pick some nouns-like words as title (naive)
            title = " ".join([w.strip(".,") for w in words[:7]])
            return title.capitalize()
        if "sentiment" in prompt or "настроение" in prompt:
            for p in ["неудов", "негат", "плох", "критик", "провал"]:
                if p in low:
                    return "negative"
            for p in ["хорош", "позит", "польз", "рост", "успех"]:
                if p in low:
                    return "positive"
            return random.choice(["neutral", "positive", "negative"])
        if "теги" in prompt or "keywords" in prompt:
            # simple tag extraction: take top frequent words
            tokens = [t.strip(".,()\"'") for t in low.split() if len(t)>4]
            tags = list(dict.fromkeys(tokens))[:5]
            return ",".join(tags) or "general"
        if "insight" in prompt or "инсайт" in prompt:
            # heuristics
            return "true" if "инсайт" in low or "важно" in low or "эксклюзив" in low else "false"

        # fallback short answer
        return "mocked response"

    def _real_generate(self, prompt: str, system_prompt: str, max_tokens: int) -> str:
        # ===== TEMPLATE =====
        # Implement the call to GigaChat API here. Example pseudo-code:
        #
        # import requests
        # headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        # data = {"model":"giga-chat-model", "prompt": system_prompt + "\n" + prompt, "max_tokens": max_tokens}
        # resp = requests.post(self.endpoint, headers=headers, json=data, timeout=30)
        # resp.raise_for_status()
        # return resp.json()["choices"][0]["text"]
        #
        # Replace above with real provider specifics.
        raise NotImplementedError("Real LLM mode not implemented. Fill in _real_generate with your GigaChat API call.")

import logging
from typing import List, Dict, AsyncGenerator
from groq import AsyncGroq
from app.config.settings import settings

logger = logging.getLogger(__name__)

class GroqClient:
    def __init__(self):
        self.api_key = settings.groq_api_key
        self.model = settings.groq_model
        self._client = None

    @property
    def client(self) -> AsyncGroq:
        if self._client is None:
            self._client = AsyncGroq(api_key=self.api_key)
        return self._client

    async def get_chat_response(self, messages: List[Dict[str, str]], temperature: float = 0.2) -> str:
        try:
            r = await self.client.chat.completions.create(
                model=self.model, messages=messages, temperature=temperature, max_tokens=4096
            )
            return r.choices[0].message.content
        except Exception as e:
            logger.error(f"Groq connectivity failure details: {e}")
            return f"Error connecting to LLM routing layers: {str(e)}"
import logging
from typing import List, Dict, Any, AsyncGenerator
from groq import AsyncGroq
from app.config.settings import settings

logger = logging.getLogger(__name__)

class GroqClient:
    def __init__(self):
        self.api_key = settings.groq_api_key
        self.model = settings.groq_model
        self._client = None
        
        if not self.api_key:
            logger.error("GROQ_API_KEY environment variable is not configured. LLM calls will fail.")

    @property
    def client(self) -> AsyncGroq:
        if self._client is None:
            if not self.api_key:
                raise ValueError("GROQ_API_KEY is required to initialize GroqClient. Please set it in your .env file.")
            self._client = AsyncGroq(api_key=self.api_key)
        return self._client

    async def get_chat_response(self, messages: List[Dict[str, str]], temperature: float = 0.2) -> str:
        """Fetch a complete (non-streaming) response from Groq."""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=4096
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error calling Groq API: {e}")
            return f"Error: Failed to fetch response from Groq API. Detail: {str(e)}"

    async def get_chat_response_stream(self, messages: List[Dict[str, str]], temperature: float = 0.2) -> AsyncGenerator[str, None]:
        """Fetch a streaming response from Groq, yielding text chunks as they arrive."""
        try:
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=4096,
                stream=True
            )
            async for chunk in stream:
                content = chunk.choices[0].delta.content
                if content:
                    yield content
        except Exception as e:
            logger.error(f"Error calling streaming Groq API: {e}")
            yield f"\n\n[Error from Groq API: {str(e)}]"

import json
import logging
from app.llm.groq_client import GroqClient

logger = logging.getLogger(__name__)

class ArchitectureSummarizer:
    def __init__(self, groq_client: GroqClient):
        self.groq_client = groq_client

    async def generate_summary(self, owner: str, repo: str, file_tree: list, readme: str) -> dict:
        prompt = f"Analyze repository structure layout {owner}/{repo}. Readme summary: {readme[:2000]}. Return explicit JSON matching fields: purpose, tech_stack, architecture_overview."
        messages = [
            {"role": "system", "content": "You are an enterprise system software architect. Output valid JSON objects only."},
            {"role": "user", "content": prompt}
        ]
        raw = await self.groq_client.get_chat_response(messages)
        try:
            return json.loads(raw.strip().strip("```json").strip("```").strip())
        except Exception:
            return {"purpose": "Code base repository index visualization context workspace map", "tech_stack": "Python, Multi-Language Grammars", "architecture_overview": raw}
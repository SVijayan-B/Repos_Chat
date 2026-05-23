import asyncio
import aiohttp
import logging
from typing import Dict, Any, Optional
from app.config.settings import settings

logger = logging.getLogger(__name__)

class GitHubClient:
    def __init__(self):
        self.token = settings.github_pat
        self.headers = {"Accept": "application/vnd.github.v3+json"}
        if self.token:
            self.headers["Authorization"] = f"Bearer {self.token}"

    async def _request_with_retry(self, session: aiohttp.ClientSession, url: str) -> Optional[Any]:
        backoff = 1.0
        for attempt in range(5):
            try:
                async with session.request("GET", url, headers=self.headers, timeout=30) as r:
                    if r.status == 200:
                        return await r.json() if "application/json" in r.headers.get("Content-Type", "") else await r.text()
                    if r.status == 403:
                        logger.warning("Rate limits encountered. Retrying...")
                    if r.status == 404:
                        return None
            except Exception as e:
                logger.error(f"Network error on attempt {attempt+1}: {e}")
            await asyncio.sleep(backoff)
            backoff *= 2
        return None
    
    async def get_tree(self, owner: str, repo: str, branch: str = "main") -> Optional[Dict[str, Any]]:
        url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
        async with aiohttp.ClientSession() as session:
            result = await self._request_with_retry(session, url)
            return result if isinstance(result, dict) else None

    async def get_file_content(self, owner: str, repo: str, branch: str, path: str) -> Optional[str]:
        url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}"
        async with aiohttp.ClientSession() as session:
            content = await self._request_with_retry(session, url)
            return content if isinstance(content, str) else None
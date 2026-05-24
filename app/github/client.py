import asyncio
import aiohttp
import logging
import time
from typing import Dict, Any, Optional
from app.config.settings import settings

logger = logging.getLogger(__name__)

class GitHubClient:
    def __init__(self):
        self.token = settings.github_pat
        self.headers = {
            "Accept": "application/vnd.github.v3+json"
        }
        if self.token:
            # Token can be prefixed with Bearer or token, GitHub accepts both
            self.headers["Authorization"] = f"Bearer {self.token}"
        else:
            logger.warning("No GitHub PAT provided. Access will be limited by GitHub rate-limits (60 requests/hr).")

    async def _request_with_retry(self, session: aiohttp.ClientSession, url: str, method: str = "GET") -> Optional[Any]:
        backoff = 1.0
        max_retries = 5
        
        for attempt in range(max_retries):
            try:
                async with session.request(method, url, headers=self.headers, timeout=30) as response:
                    # Check rate limits
                    remaining = response.headers.get("X-RateLimit-Remaining")
                    reset_time = response.headers.get("X-RateLimit-Reset")
                    
                    if remaining is not None:
                        logger.debug(f"GitHub Rate Limit Remaining: {remaining}")
                    
                    if response.status == 200:
                        if "application/json" in response.headers.get("Content-Type", ""):
                            return await response.json()
                        return await response.text()
                    
                    elif response.status in (403, 429):
                        # Rate limit reached
                        if reset_time:
                            sleep_duration = max(float(reset_time) - time.time() + 1, 1.0)
                            logger.warning(f"Rate limit hit. Sleeping for {sleep_duration:.2f} seconds until reset.")
                        else:
                            sleep_duration = backoff * 2
                            logger.warning(f"Rate limit hit (no reset header). Sleeping for {sleep_duration} seconds.")
                        await asyncio.sleep(sleep_duration)
                        backoff *= 2
                        continue
                    
                    elif response.status == 404:
                        logger.error(f"GitHub resource not found (404): {url}")
                        return None
                    
                    else:
                        logger.warning(f"GitHub request failed ({response.status}) on attempt {attempt+1}: {url}")
                        await asyncio.sleep(backoff)
                        backoff *= 2
            
            except Exception as e:
                logger.error(f"Network error in GitHub client (attempt {attempt+1}): {e}")
                await asyncio.sleep(backoff)
                backoff *= 2
                
        logger.error(f"Failed to fetch resource after {max_retries} retries: {url}")
        return None

    async def get_tree(self, owner: str, repo: str, branch: str = "main") -> Optional[Dict[str, Any]]:
        """Fetch repository tree recursively using GitHub REST API."""
        url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
        logger.info(f"Fetching repository tree: {owner}/{repo} (branch: {branch})")
        
        async with aiohttp.ClientSession() as session:
            result = await self._request_with_retry(session, url)
            if isinstance(result, dict):
                return result
            return None

    async def get_file_content(self, owner: str, repo: str, branch: str, path: str) -> Optional[str]:
        """Fetch raw file content asynchronously from GitHub User Content."""
        # Note: Raw Github Content URL accepts Bearer token headers for public (and private repositories)
        url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}"
        logger.debug(f"Fetching raw file: {path}")
        
        async with aiohttp.ClientSession() as session:
            content = await self._request_with_retry(session, url)
            if isinstance(content, str):
                return content
            return None

"""Cloud API wrapper — shared HTTP client for free-tier video gen APIs."""

import asyncio
import httpx
from pathlib import Path
from typing import Optional
from src.utils.logger import setup_logger


class CloudAPIWrapper:
    """Shared HTTP client with retry, rate limiting, and free-tier quota handling.

    Supports Hugging Face Inference API, Replicate, and FAL.ai.
    """

    def __init__(self, logger=None):
        self.logger = logger or setup_logger()
        self._client: Optional[httpx.AsyncClient] = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=300.0)
        return self._client

    async def post(self, url: str, headers: dict, json_body: dict = None, data: bytes = None, max_retries: int = 3):
        """POST with retry and exponential backoff. Returns dict (JSON) or raw bytes."""
        client = self._get_client()
        for attempt in range(max_retries):
            try:
                if json_body is not None:
                    resp = await client.post(url, headers=headers, json=json_body)
                elif data is not None:
                    resp = await client.post(url, headers=headers, content=data)
                else:
                    resp = await client.post(url, headers=headers)
                if resp.status_code == 429:
                    wait = 2 ** attempt * 5
                    self.logger.warning(f"Rate limited, waiting {wait}s")
                    await asyncio.sleep(wait)
                    continue
                if resp.status_code == 503:
                    wait = 2 ** attempt * 10
                    self.logger.warning(f"Model loading, waiting {wait}s")
                    await asyncio.sleep(wait)
                    continue
                resp.raise_for_status()
                content_type = resp.headers.get("content-type", "")
                if "application/json" in content_type:
                    return resp.json()
                return resp.content  # raw bytes for video/binary responses
            except httpx.HTTPStatusError as e:
                if attempt == max_retries - 1:
                    raise
                self.logger.warning(f"HTTP error {e.response.status_code}, retrying...")
                await asyncio.sleep(2 ** attempt)
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                self.logger.warning(f"Request failed: {e}, retrying...")
                await asyncio.sleep(2 ** attempt)
        raise RuntimeError("Max retries exceeded")

    async def download_file(self, url: str, output_path: Path, headers: Optional[dict] = None) -> Path:
        """Download a file from URL to output_path."""
        client = self._get_client()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        async with client.stream("GET", url, headers=headers or {}) as resp:
            resp.raise_for_status()
            with open(output_path, "wb") as f:
                async for chunk in resp.aiter_bytes(chunk_size=8192):
                    f.write(chunk)
        return output_path

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None

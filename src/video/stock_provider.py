"""Stock video provider — download free CC/PD videos from Wikimedia Commons & Internet Archive.

No API keys or registration required. Searches for real footage matching
the scene's visual prompt keywords.
"""

import asyncio
import httpx
import re
from pathlib import Path
from src.models.scene import VideoResult
from src.config import Config
from src.utils.ffmpeg import resolve_ffmpeg, run_ffmpeg
from src.utils.logger import setup_logger

# Common words to skip when extracting search keywords
STOP_WORDS = {
    "a", "an", "the", "in", "on", "at", "to", "for", "of", "with", "by", "from",
    "is", "are", "was", "were", "be", "been", "being", "have", "has", "had",
    "do", "does", "did", "will", "would", "could", "should", "may", "might",
    "and", "or", "but", "not", "no", "so", "if", "then", "than", "that", "this",
    "it", "its", "he", "she", "they", "we", "i", "you", "my", "your", "his",
    "her", "our", "their", "me", "him", "us", "them", "what", "which", "who",
    "when", "where", "why", "how", "all", "each", "every", "both", "few", "more",
    "most", "other", "some", "such", "only", "own", "same", "too", "very",
    "can", "just", "should", "now", "cinematic", "widescreen", "framing",
    "professional", "color", "grading", "film", "grain", "depth", "field",
    "high", "production", "value", "broadcast", "quality", "resolution",
    "shot", "camera", "lighting", "pan", "dolly", "tracking", "zoom",
    "slow", "gentle", "dramatic", "soft", "golden", "hour", "natural",
    "motion", "movement", "parallax", "crane", "handheld", "static",
    "wide", "close", "up", "aerial", "overhead", "low", "angle",
}

USER_AGENT = "cinematic-video-engine/1.0 (contact@example.com)"


def extract_keywords(prompt: str, max_keywords: int = 4) -> str:
    """Extract search keywords from a visual prompt."""
    words = re.findall(r"[a-zA-Z]+", prompt.lower())
    keywords = [w for w in words if w not in STOP_WORDS and len(w) > 2]
    # Deduplicate while preserving order
    seen = set()
    unique = []
    for k in keywords:
        if k not in seen:
            seen.add(k)
            unique.append(k)
    return " ".join(unique[:max_keywords])


class StockVideoProvider:
    """Download free CC/PD videos from Wikimedia Commons and Internet Archive."""

    def __init__(self, config: Config):
        self.config = config
        self.logger = setup_logger(config.log_level)
        self._client = httpx.AsyncClient(timeout=60.0, follow_redirects=True, headers={
            "User-Agent": "cinematic-video-engine/1.0 (contact@example.com)",
            "Accept": "application/json",
        })
        self._cache_dir = Path(config.temp_dir) / "stock_cache"
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    async def generate(self, prompt: str, duration_seconds: float, output_path: Path) -> VideoResult:
        """Search for and download a free stock video matching the prompt."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        keywords = extract_keywords(prompt)
        self.logger.info(f"Stock search keywords: {keywords}")

        # Try Wikimedia Commons first
        # Try Wikimedia Commons first (with timeout)
        try:
            video_path = await asyncio.wait_for(
                self._search_wikimedia(keywords, output_path), timeout=15.0
            )
            if video_path:
                return await self._normalize(video_path, output_path, duration_seconds)
        except asyncio.TimeoutError:
            self.logger.warning("Wikimedia search timed out")

        # Fall back to Internet Archive (with timeout)
        try:
            video_path = await asyncio.wait_for(
                self._search_archive(keywords, output_path), timeout=20.0
            )
            if video_path:
                return await self._normalize(video_path, output_path, duration_seconds)
        except asyncio.TimeoutError:
            self.logger.warning("Archive search timed out")

        # Last resort: use mock provider
        self.logger.warning("No stock video found, falling back to mock provider")
        from src.video.mock_provider import MockVideoProvider
        mock = MockVideoProvider(self.config)
        return await mock.generate(prompt, duration_seconds, output_path)

    async def _search_wikimedia(self, keywords: str, output_path: Path) -> Path | None:
        """Search Wikimedia Commons for video files."""
        try:
            params = {
                "action": "query",
                "generator": "search",
                "gsrsearch": keywords,
                "gsrnamespace": 6,
                "gsrlimit": 10,
                "prop": "imageinfo",
                "iiprop": "url|size|mime|extmetadata",
                "format": "json",
            }
            resp = await self._client.get("https://commons.wikimedia.org/w/api.php", params=params)
            resp.raise_for_status()
            data = resp.json()

            pages = data.get("query", {}).get("pages", {})
            for page in pages.values():
                ii = page.get("imageinfo", [{}])[0]
                mime = ii.get("mime", "")
                if not mime.startswith("video/"):
                    continue
                url = ii.get("url")
                if not url:
                    continue
                # Prefer smaller files for faster download
                size = ii.get("size", 0)
                if size > 50_000_000:  # skip files > 50MB
                    continue

                self.logger.info(f"Found Wikimedia video: {url}")
                return await self._download(url, output_path)
        except Exception as e:
            self.logger.warning(f"Wikimedia search failed: {e}")
        return None

    async def _search_archive(self, keywords: str, output_path: Path) -> Path | None:
        """Search Internet Archive for video files."""
        try:
            search_url = "https://archive.org/advancedsearch.php"
            params = {
                "q": f'mediatype:movies AND ({keywords.replace(" ", " OR ")})',
                "fl[]": ["identifier", "title"],
                "rows": 5,
                "output": "json",
            }
            resp = await self._client.get(search_url, params=params)
            resp.raise_for_status()
            docs = resp.json().get("response", {}).get("docs", [])

            for doc in docs:
                ident = doc.get("identifier")
                if not ident:
                    continue
                meta_resp = await self._client.get(f"https://archive.org/metadata/{ident}")
                meta = meta_resp.json()
                for f in meta.get("files", []):
                    name = f.get("name", "")
                    if not name.lower().endswith((".mp4", ".webm", ".ogv", ".mov")):
                        continue
                    size = f.get("size", 0)
                    if isinstance(size, str):
                        size = int(size) if size.isdigit() else 0
                    if size > 50_000_000:
                        continue
                    url = f"https://archive.org/download/{ident}/{name}"
                    self.logger.info(f"Found Archive video: {url}")
                    result = await self._download(url, output_path)
                    if result:
                        return result
        except Exception as e:
            self.logger.warning(f"Archive search failed: {e}")
        return None

    async def _download(self, url: str, output_path: Path) -> Path | None:
        """Download a video file from URL."""
        try:
            async with self._client.stream("GET", url) as resp:
                resp.raise_for_status()
                with open(output_path, "wb") as f:
                    async for chunk in resp.aiter_bytes(chunk_size=8192):
                        f.write(chunk)
            if output_path.exists() and output_path.stat().st_size > 1000:
                self.logger.info(f"Downloaded: {output_path} ({output_path.stat().st_size} bytes)")
                return output_path
        except Exception as e:
            self.logger.warning(f"Download failed: {e}")
            if output_path.exists():
                output_path.unlink()
        return None

    async def _normalize(self, video_path: Path, output_path: Path, duration_seconds: float) -> VideoResult:
        """Normalize downloaded video to 1920x1080, 30fps, H.264."""
        ffmpeg = await resolve_ffmpeg(self.config.ffmpeg_path)
        # Trim or loop to match requested duration
        args = [
            ffmpeg, "-y", "-i", str(video_path),
            "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30",
            "-t", str(duration_seconds),
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-an", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
            str(output_path),
        ]
        rc, stdout, stderr = await run_ffmpeg(args)
        if rc != 0:
            self.logger.warning(f"Normalize failed: {stderr[-300:]}")
            # Fall back to mock
            from src.video.mock_provider import MockVideoProvider
            mock = MockVideoProvider(self.config)
            return await mock.generate("", duration_seconds, output_path)
        duration_ms = int(duration_seconds * 1000)
        return VideoResult(file=str(output_path), duration_ms=duration_ms, provider="stock")

    async def close(self):
        await self._client.aclose()

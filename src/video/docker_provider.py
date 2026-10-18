"""Docker video provider — calls local Docker container running CogVideoX-2B.

The Docker container runs a FastAPI server at localhost:8188 that
generates video from text prompts using CogVideoX-2B (CPU inference).
"""

import asyncio
import httpx
from pathlib import Path
from src.models.scene import VideoResult
from src.config import Config
from src.utils.ffmpeg import resolve_ffmpeg, run_ffmpeg
from src.utils.logger import setup_logger


class DockerVideoProvider:
    """Video generation via local Docker container (CogVideoX-2B)."""

    def __init__(self, config: Config):
        self.config = config
        self.logger = setup_logger(config.log_level)
        self.base_url = getattr(config, "docker_video_url", "http://localhost:8188")

    async def generate(self, prompt: str, duration_seconds: float, output_path: Path) -> VideoResult:
        """Generate a video clip via the local Docker API."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        num_frames = max(8, int(duration_seconds * 8))  # 8fps

        self.logger.info(f"Docker video gen: prompt='{prompt[:60]}...', frames={num_frames}")

        async with httpx.AsyncClient(timeout=600.0) as client:
            # Check health first
            try:
                health = await client.get(f"{self.base_url}/health")
                if health.status_code != 200:
                    raise RuntimeError(f"Docker video gen not ready: {health.status_code}")
            except httpx.ConnectError:
                raise RuntimeError(
                    f"Cannot connect to Docker video gen at {self.base_url}. "
                    "Is the container running? Start with: docker compose -f docker/docker-compose.yml up"
                )

            # Request generation
            resp = await client.post(
                f"{self.base_url}/generate",
                json={
                    "prompt": prompt[:200],
                    "num_frames": num_frames,
                    "num_inference_steps": 20,  # lower for CPU speed
                    "guidance_scale": 6.0,
                },
            )

            if resp.status_code != 200:
                raise RuntimeError(f"Docker video gen failed: {resp.status_code} {resp.text}")

            data = resp.json()
            filename = data.get("file")
            duration_ms = data.get("duration_ms", int(duration_seconds * 1000))

            if not filename:
                raise RuntimeError("No video file returned from Docker API")

            # Download the video
            video_url = f"{self.base_url}/video/{filename}"
            async with client.stream("GET", video_url) as stream:
                stream.raise_for_status()
                with open(output_path, "wb") as f:
                    async for chunk in stream.aiter_bytes(chunk_size=8192):
                        f.write(chunk)

            if not output_path.exists() or output_path.stat().st_size < 1000:
                raise RuntimeError("Downloaded video is empty or too small")

            # Normalize to 1920x1080, 30fps, H.264
            ffmpeg = await resolve_ffmpeg(self.config.ffmpeg_path)
            normalized = output_path.with_suffix(".norm.mp4")
            args = [
                ffmpeg, "-y", "-i", str(output_path),
                "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30",
                "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                "-an", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                str(normalized),
            ]
            rc, _, stderr = await run_ffmpeg(args)
            if rc == 0 and normalized.exists():
                normalized.replace(output_path)
            else:
                self.logger.warning(f"Normalization failed, using raw video: {stderr[-200:]}")

            self.logger.info(f"Docker video generated: {output_path} ({duration_ms}ms)")
            return VideoResult(file=str(output_path), duration_ms=duration_ms, provider="docker-cogvideox")
"""Mock video provider — generates synthetic 16:9 video clips using FFmpeg.

No API keys, no GPU needed. Creates colored background with text overlay
for testing the full pipeline end-to-end.
"""

from pathlib import Path
from src.models.scene import VideoResult
from src.config import Config
from src.utils.ffmpeg import resolve_ffmpeg, run_ffmpeg
from src.utils.logger import setup_logger


class MockVideoProvider:
    """Generate synthetic video clips using FFmpeg (free, no API keys)."""

    COLORS = ["0x1a1a2e", "0x16213e", "0x0f3460", "0x533483", "0x2c3e50", "0x34495e"]

    def __init__(self, config: Config):
        self.config = config
        self.logger = setup_logger(config.log_level)

    async def generate(self, prompt: str, duration_seconds: float, output_path: Path) -> VideoResult:
        """Generate a synthetic 16:9 video clip with text overlay."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        ffmpeg = await resolve_ffmpeg(self.config.ffmpeg_path)
        color = self.COLORS[hash(prompt) % len(self.COLORS)]

        # Generate a simple colored background video (no text overlay to avoid
        # FFmpeg drawtext escaping issues with special characters)
        args = [
            ffmpeg, "-y", "-f", "lavfi",
            "-i", f"color=c={color}:s=1920x1080:r=30:d={duration_seconds}",
            "-vf", "format=yuv420p",
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart",
            str(output_path),
        ]
        rc, stdout, stderr = await run_ffmpeg(args)
        if rc != 0:
            raise RuntimeError(f"Mock video gen failed: {stderr[-500:]}")

        duration_ms = int(duration_seconds * 1000)
        self.logger.info(f"Mock video generated: {output_path} ({duration_ms}ms)")
        return VideoResult(file=str(output_path), duration_ms=duration_ms, provider="mock")

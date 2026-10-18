"""Mock video provider — generates animated 16:9 video clips using FFmpeg.

Creates animated backgrounds with color shifting, vignette, and film grain
for a cinematic feel — no API keys or GPU needed.
"""

from pathlib import Path
from src.models.scene import VideoResult
from src.config import Config
from src.utils.ffmpeg import resolve_ffmpeg, run_ffmpeg
from src.utils.logger import setup_logger


class MockVideoProvider:
    """Generate animated video clips using FFmpeg effects."""

    COLORS = [
        "0x1a1a2e", "0x16213e", "0x0f3460", "0x533483",
        "0x2c3e50", "0x34495e", "0x1e3c72", "0x2a5298",
        "0x0f2027", "0x203a43", "0x232526", "0x414345",
    ]

    def __init__(self, config: Config):
        self.config = config
        self.logger = setup_logger(config.log_level)

    async def generate(self, prompt: str, duration_seconds: float, output_path: Path) -> VideoResult:
        """Generate an animated 16:9 video clip."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        ffmpeg = await resolve_ffmpeg(self.config.ffmpeg_path)
        color = self.COLORS[hash(prompt) % len(self.COLORS)]
        # Subtle brightness oscillation seed
        seed = abs(hash(prompt)) % 100

        # Filter chain: color shift + vignette + film grain
        # Keep it simple and fast to avoid FFmpeg timeout
        vf = (
            f"colorbalance=rs={0.02 + seed % 5 * 0.01}:bs={-0.02 + seed % 3 * 0.01},"
            f"vignette=PI/4,"
            f"noise=alls=4:allf=t"
        )

        args = [
            ffmpeg, "-y", "-f", "lavfi",
            "-i", f"color=c={color}:s=1920x1080:r=30:d={duration_seconds}",
            "-vf", vf,
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart",
            str(output_path),
        ]
        rc, stdout, stderr = await run_ffmpeg(args, timeout=120)
        if rc != 0:
            # Absolute fallback: plain color
            self.logger.warning(f"Filter failed, using plain color: {stderr[-200:]}")
            args = [
                ffmpeg, "-y", "-f", "lavfi",
                "-i", f"color=c={color}:s=1920x1080:r=30:d={duration_seconds}",
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
                "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                str(output_path),
            ]
            rc, stdout, stderr = await run_ffmpeg(args, timeout=120)
            if rc != 0:
                raise RuntimeError(f"Mock video gen failed: {stderr[-500:]}")

        duration_ms = int(duration_seconds * 1000)
        self.logger.info(f"Animated mock video generated: {output_path} ({duration_ms}ms)")
        return VideoResult(file=str(output_path), duration_ms=duration_ms, provider="mock-animated")

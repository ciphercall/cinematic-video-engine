"""FFmpeg subprocess wrapper — resolve, run, probe."""

import asyncio
import shutil
from pathlib import Path
from typing import Optional


async def resolve_ffmpeg(ffmpeg_path: str = "ffmpeg") -> str:
    """Resolve the FFmpeg binary path."""
    resolved = shutil.which(ffmpeg_path)
    if resolved is None:
        # Try common locations
        for candidate in ["/usr/bin/ffmpeg", "/usr/local/bin/ffmpeg", "C:\\ffmpeg\\bin\\ffmpeg.exe"]:
            if Path(candidate).exists():
                return candidate
        raise RuntimeError(
            "FFmpeg not found. Install FFmpeg and ensure it's on PATH, "
            "or set FFMPEG_PATH in .env"
        )
    return resolved


async def run_ffmpeg(args: list[str], cwd: Optional[str] = None, timeout: int = 600) -> tuple[int, str, str]:
    """Run FFmpeg with the given argument list. Returns (returncode, stdout, stderr)."""
    proc = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        raise RuntimeError(f"FFmpeg timed out after {timeout}s")
    return proc.returncode, stdout.decode(errors="replace"), stderr.decode(errors="replace")


async def probe_duration(file_path: str, ffprobe_path: str = "ffprobe") -> float:
    """Get media duration in seconds via ffprobe."""
    # Resolve ffprobe path (may be full path from config)
    resolved = ffprobe_path if ffprobe_path != "ffprobe" else None
    if resolved is None:
        import shutil
        resolved = shutil.which("ffprobe") or "ffprobe"
    proc = await asyncio.create_subprocess_exec(
        resolved, "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", file_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await proc.communicate()
    try:
        return float(stdout.decode().strip())
    except ValueError:
        return 0.0


async def probe_resolution(file_path: str, ffprobe_path: str = "ffprobe") -> tuple[int, int]:
    """Get video resolution (width, height) via ffprobe."""
    proc = await asyncio.create_subprocess_exec(
        ffprobe_path, "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height", "-of", "csv=s=x:p=0", file_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await proc.communicate()
    parts = stdout.decode().strip().split("x")
    if len(parts) == 2:
        return int(parts[0]), int(parts[1])
    return 0, 0

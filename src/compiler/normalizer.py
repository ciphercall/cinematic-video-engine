"""Clip normalizer — ensure all clips are 1920x1080, 30fps, H.264."""

import asyncio
from pathlib import Path
from src.utils.ffmpeg import resolve_ffmpeg, run_ffmpeg
from src.config import Config


async def normalize_clip(input_path: Path, output_path: Path, config: Config) -> Path:
    """Normalize a video clip to 1920x1080, 30fps, H.264/AAC.

    Ensures all scene clips have identical codec, resolution, and fps
    for seamless FFmpeg concatenation.
    """
    ffmpeg = await resolve_ffmpeg(config.ffmpeg_path)
    args = [
        ffmpeg, "-y", "-i", str(input_path),
        "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-c:a", "aac", "-ar", "48000", "-ac", "2",
        "-movflags", "+faststart",
        str(output_path),
    ]
    rc, stdout, stderr = await run_ffmpeg(args)
    if rc != 0:
        raise RuntimeError(f"FFmpeg normalize failed: {stderr[-500:]}")
    return output_path


async def normalize_all(clips: list[Path], output_dir: Path, config: Config) -> list[Path]:
    """Normalize a list of clips in parallel."""
    import asyncio
    output_dir.mkdir(parents=True, exist_ok=True)
    tasks = []
    for i, clip in enumerate(clips):
        out = output_dir / f"normalized_{i:03d}.mp4"
        tasks.append(normalize_clip(clip, out, config))
    return await asyncio.gather(*tasks)

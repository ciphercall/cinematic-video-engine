"""Subtitle burner — burn ASS/SRT subtitles onto a video via FFmpeg."""

from pathlib import Path
from src.utils.ffmpeg import resolve_ffmpeg, run_ffmpeg
from src.config import Config


async def burn_subtitles(video_path: Path, subtitle_path: Path, output_path: Path, config: Config) -> Path:
    """Burn subtitle file (ASS or SRT) onto a video.

    Args:
        video_path: Input video file.
        subtitle_path: ASS or SRT subtitle file.
        output_path: Output video file with burned subtitles.
        config: Application config.
    """
    ffmpeg = await resolve_ffmpeg(config.ffmpeg_path)
    subtitle_path = Path(subtitle_path)

    # FFmpeg subtitles filter needs forward slashes and escaped colon on Windows
    sub_path_str = str(subtitle_path.resolve()).replace("\\", "/").replace(":", "\\:")

    if subtitle_path.suffix.lower() == ".ass":
        vf = f"subtitles='{sub_path_str}'"
    else:
        vf = f"subtitles='{sub_path_str}':force_style='FontName={config.subtitle_font},FontSize={config.subtitle_font_size},PrimaryColour=&H00{config.subtitle_color},OutlineColour=&H00{config.subtitle_outline_color},Outline={config.subtitle_outline_width}'"

    args = [
        ffmpeg, "-y", "-i", str(video_path),
        "-vf", vf,
        "-c:v", "libx264", "-crf", "18", "-preset", "medium",
        "-c:a", "copy", "-movflags", "+faststart",
        str(output_path),
    ]
    rc, _, stderr = await run_ffmpeg(args)
    if rc != 0:
        raise RuntimeError(f"FFmpeg subtitle burn failed: {stderr[-500:]}")
    return output_path

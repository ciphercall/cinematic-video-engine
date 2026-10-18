"""Subtitle generation — word-level SRT and ASS (karaoke) output."""

from pathlib import Path
from typing import List
from src.models.scene import Scene
from src.config import Config


def generate_ass(scenes: List[Scene], config: Config, output_path: Path) -> Path:
    """Generate an ASS subtitle file with word-by-word karaoke timing.

    Uses word_timings from each scene's TTS result.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # ASS header
    lines = [
        "[Script Info]",
        "Title: Cinematic Video Subtitles",
        "ScriptType: v4.00+",
        "WrapStyle: 0",
        "ScaledBorderAndShadow: yes",
        "YCbCr Matrix: None",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: Default,{config.subtitle_font},{config.subtitle_font_size},&H00{config.subtitle_color},&H00{config.subtitle_color},&H00{config.subtitle_outline_color},&H00000000,0,0,0,0,100,100,0,0,1,{config.subtitle_outline_width},1,2,30,30,40,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]

    offset_ms = 0
    for scene in scenes:
        if not scene.word_timings:
            # Fallback: show full narration for scene duration
            start = _ms_to_ass_time(offset_ms)
            end = _ms_to_ass_time(offset_ms + scene.audio_duration_ms)
            text = scene.narration_text.replace("\n", "\\N")
            lines.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}")
            offset_ms += scene.audio_duration_ms or int(scene.estimated_duration * 1000)
            continue

        # Word-by-word karaoke: group words into subtitle lines (max ~8 words per line)
        words = scene.word_timings
        chunk_size = 8
        for chunk_start in range(0, len(words), chunk_size):
            chunk = words[chunk_start:chunk_start + chunk_size]
            if not chunk:
                continue
            line_start_ms = offset_ms + chunk[0]["start_ms"]
            line_end_ms = offset_ms + chunk[-1]["end_ms"]

            # Build karaoke text with \k tags
            karaoke_parts = []
            for w in chunk:
                dur_cs = max(1, (w["end_ms"] - w["start_ms"]) // 10)  # centiseconds
                karaoke_parts.append(f"{{\\k{dur_cs}}}{w['word']}")

            text = " ".join(karaoke_parts)
            start = _ms_to_ass_time(line_start_ms)
            end = _ms_to_ass_time(line_end_ms)
            lines.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}")

        offset_ms += scene.audio_duration_ms or int(scene.estimated_duration * 1000)

    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def generate_srt(scenes: List[Scene], output_path: Path) -> Path:
    """Generate a standard SRT subtitle file (one entry per scene)."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    entries = []
    offset_ms = 0
    for i, scene in enumerate(scenes, 1):
        start_ms = offset_ms
        end_ms = offset_ms + (scene.audio_duration_ms or int(scene.estimated_duration * 1000))
        entries.append(
            f"{i}\n"
            f"{_ms_to_srt_time(start_ms)} --> {_ms_to_srt_time(end_ms)}\n"
            f"{scene.narration_text}\n"
        )
        offset_ms = end_ms

    output_path.write_text("\n".join(entries), encoding="utf-8")
    return output_path


def _ms_to_ass_time(ms: int) -> str:
    """Convert milliseconds to ASS time format H:MM:SS.cc"""
    h = ms // 3600000
    m = (ms % 3600000) // 60000
    s = (ms % 60000) // 1000
    cs = (ms % 1000) // 10
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _ms_to_srt_time(ms: int) -> str:
    """Convert milliseconds to SRT time format HH:MM:SS,mmm"""
    h = ms // 3600000
    m = (ms % 3600000) // 60000
    s = (ms % 60000) // 1000
    millis = ms % 1000
    return f"{h:02d}:{m:02d}:{s:02d},{millis:03d}"

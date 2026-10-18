"""Video assembler — FFmpeg stitching, audio overlay, subtitle burning."""

import asyncio
from pathlib import Path
from typing import List
from src.models.scene import Scene
from src.config import Config
from src.utils.ffmpeg import resolve_ffmpeg, run_ffmpeg, probe_duration
from src.utils.file_manager import ensure_dir
from src.audio.subtitle import generate_ass


async def assemble(scenes: List[Scene], output_dir: Path, config: Config, subtitles: bool = True) -> Path:
    """Assemble final video from scenes: normalize → concat → audio overlay → subtitle burn.

    Returns path to final .mp4.
    """
    output_dir = Path(output_dir)
    ensure_dir(output_dir)
    tmp_dir = output_dir / ".tmp"
    ensure_dir(tmp_dir)

    ffmpeg = await resolve_ffmpeg(config.ffmpeg_path)

    # 1. Normalize all clips
    from src.compiler.normalizer import normalize_all
    clips = [Path(s.video_file) for s in scenes if s.video_file]
    normalized = await normalize_all(clips, tmp_dir / "normalized", config)

    # 2. Concatenate clips
    concat_list = tmp_dir / "concat_list.txt"
    concat_list.write_text("\n".join(f"file '{p.resolve()}'" for p in normalized), encoding="utf-8")
    concat_output = tmp_dir / "concat.mp4"
    args = [ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list), "-c", "copy", str(concat_output)]
    rc, _, stderr = await run_ffmpeg(args)
    if rc != 0:
        raise RuntimeError(f"FFmpeg concat failed: {stderr[-500:]}")

    # 3. Generate ASS subtitles if enabled
    ass_path = None
    if subtitles:
        ass_path = tmp_dir / "subtitles.ass"
        generate_ass(scenes, config, ass_path)

    # 4. Build audio track: concatenate per-scene audio with silence padding
    audio_concat_list = tmp_dir / "audio_concat_list.txt"
    audio_segments = []
    for scene in scenes:
        video_dur = scene.video_duration_ms or int(scene.estimated_duration * 1000)
        if scene.audio_file and Path(scene.audio_file).exists():
            audio_segments.append(f"file '{Path(scene.audio_file).resolve()}'")
            # Pad with silence if audio shorter than video
            gap = video_dur - scene.audio_duration_ms
            if gap > 100:
                silence_path = tmp_dir / f"silence_{scene.index}.mp3"
                silence_args = [ffmpeg, "-y", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
                                "-t", str(gap / 1000), "-c:a", "libmp3lame", "-q:a", "4", str(silence_path)]
                await run_ffmpeg(silence_args)
                if silence_path.exists():
                    audio_segments.append(f"file '{silence_path.resolve()}'")
        else:
            # No audio for this scene — generate silence for full video duration
            silence_path = tmp_dir / f"silence_{scene.index}.mp3"
            silence_args = [ffmpeg, "-y", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
                            "-t", str(video_dur / 1000), "-c:a", "libmp3lame", "-q:a", "4", str(silence_path)]
            await run_ffmpeg(silence_args)
            if silence_path.exists():
                audio_segments.append(f"file '{silence_path.resolve()}'")

    if not audio_segments:
        # Fallback: generate 1 second of silence
        silence_path = tmp_dir / "silence_fallback.mp3"
        await run_ffmpeg([ffmpeg, "-y", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
                          "-t", "1", "-c:a", "libmp3lame", str(silence_path)])
        audio_segments.append(f"file '{silence_path.resolve()}'")

    audio_concat_list.write_text("\n".join(audio_segments), encoding="utf-8")

    audio_track = tmp_dir / "audio_track.mp3"
    args = [ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(audio_concat_list), "-c:a", "libmp3lame", "-q:a", "2", str(audio_track)]
    rc, _, stderr = await run_ffmpeg(args)
    if rc != 0:
        raise RuntimeError(f"FFmpeg audio concat failed: {stderr[-500:]}")

    # 5. Mix video + audio
    mixed_output = tmp_dir / "mixed.mp4"
    args = [ffmpeg, "-y", "-i", str(concat_output), "-i", str(audio_track),
            "-c:v", "copy", "-c:a", "aac", "-shortest", str(mixed_output)]
    rc, _, stderr = await run_ffmpeg(args)
    if rc != 0:
        raise RuntimeError(f"FFmpeg mix failed: {stderr[-500:]}")

    # 6. Burn subtitles
    final_output = output_dir / "final_video.mp4"
    if subtitles and ass_path and ass_path.exists():
        # Escape path for FFmpeg subtitles filter (colon in drive letter needs escaping)
        ass_path_str = str(ass_path.resolve()).replace("\\", "/").replace(":", "\\:")
        args = [ffmpeg, "-y", "-i", str(mixed_output),
                "-vf", f"subtitles='{ass_path_str}'",
                "-c:v", "libx264", "-crf", "18", "-preset", "medium",
                "-c:a", "copy", "-movflags", "+faststart", str(final_output)]
        rc, _, stderr = await run_ffmpeg(args)
        if rc != 0:
            raise RuntimeError(f"FFmpeg subtitle burn failed: {stderr[-500:]}")
    else:
        # Just copy with faststart
        args = [ffmpeg, "-y", "-i", str(mixed_output), "-c", "copy", "-movflags", "+faststart", str(final_output)]
        rc, _, stderr = await run_ffmpeg(args)
        if rc != 0:
            raise RuntimeError(f"FFmpeg final copy failed: {stderr[-500:]}")

    return final_output

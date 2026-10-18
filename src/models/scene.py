"""Scene data model — the atomic unit of the narrative pipeline."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Scene:
    """A single semantic scene in the narrative video.

    Produced by the scene parser, enhanced by the prompt builder,
    then consumed by the TTS and video generation modules.
    """

    id: str
    index: int
    narration_text: str
    visual_prompt: str
    estimated_duration: float = 5.0  # seconds, used as hint for video gen

    # Populated during generation
    audio_file: Optional[str] = None
    video_file: Optional[str] = None
    audio_duration_ms: int = 0
    video_duration_ms: int = 0
    start_offset_ms: int = 0

    # Word-level timing from TTS (for word-by-word subtitles)
    # Each entry: {"word": str, "start_ms": int, "end_ms": int}
    word_timings: list[dict] = field(default_factory=list)

    # Status tracking for checkpoint/resume
    audio_done: bool = False
    video_done: bool = False
    compiled: bool = False


@dataclass
class AudioResult:
    """Result from a TTS synthesis call."""

    file: str
    duration_ms: int
    word_timings: list[dict] = field(default_factory=list)
    provider: str = ""


@dataclass
class VideoResult:
    """Result from a video generation call."""

    file: str
    duration_ms: int
    width: int = 1920
    height: int = 1080
    provider: str = ""

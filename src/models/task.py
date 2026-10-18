"""Task state model — checkpoint/resume support for long-running pipelines."""

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class TaskState:
    """Persisted state for a pipeline run, enabling resume from last completed scene."""

    task_id: str
    input_file: str
    output_dir: str
    language: str
    tts_provider: str
    video_provider: str
    scenes: list[dict] = field(default_factory=list)  # serialized Scene list
    current_scene_index: int = 0
    status: str = "pending"  # pending | running | completed | failed
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    final_output: Optional[str] = None
    error: Optional[str] = None

    def mark_scene_audio_done(self, index: int, audio_file: str, duration_ms: int, word_timings: list[dict]):
        self.scenes[index]["audio_file"] = audio_file
        self.scenes[index]["audio_duration_ms"] = duration_ms
        self.scenes[index]["word_timings"] = word_timings
        self.scenes[index]["audio_done"] = True
        self.updated_at = datetime.now().isoformat()

    def mark_scene_video_done(self, index: int, video_file: str, duration_ms: int):
        self.scenes[index]["video_file"] = video_file
        self.scenes[index]["video_duration_ms"] = duration_ms
        self.scenes[index]["video_done"] = True
        self.updated_at = datetime.now().isoformat()

    def all_scenes_done(self) -> bool:
        return all(s.get("audio_done") and s.get("video_done") for s in self.scenes)

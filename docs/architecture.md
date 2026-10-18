# Architecture — Cinematic Video Engine

## Overview

The Cinematic Video Engine converts raw text documents into 16:9 narrative videos
with synchronized voiceovers and word-by-word subtitles. It is built as a modular
pipeline with pluggable providers for each stage.

## Module Map

| Module | Purpose | Key Files |
|--------|---------|-----------|
| `src/agents/` | Text processing & fine-tuning | `scene_parser.py`, `prompt_builder.py`, `llm_client.py` |
| `src/audio/` | Audio generation | `tts_engine.py`, `edge_tts_provider.py`, `kokoro_provider.py`, `subtitle.py` |
| `src/video/` | Video generation | `video_client.py`, `mock_provider.py`, `wan_provider.py`, `hunyuan_provider.py`, `ltx_provider.py`, `cloud_api_wrapper.py` |
| `src/compiler/` | Video assembly | `assembler.py`, `normalizer.py`, `subtitle_burner.py` |
| `src/pipelines/` | Orchestration | `narrative_pipeline.py` |
| `src/publishers/` | Future publishing slot | `base.py` (NoOpPublisher) |
| `src/models/` | Data models | `scene.py`, `task.py` |
| `src/utils/` | Shared utilities | `ffmpeg.py`, `logger.py`, `file_manager.py`, `doctor.py` |

## Data Flow

```
Input Text File
    │
    ▼
[SceneParser] ──LLM/Rule-based──► List[Scene] (narration_text, visual_prompt)
    │
    ▼
[PromptBuilder] ──enhance──► List[Scene] (cinematic prompts)
    │
    ├──► [TTS Provider] ──► .mp3/.wav + word_timings
    │
    └──► [Video Provider] ──► .mp4 clip (16:9)
    │
    ▼
[Assembler] ──FFmpeg──► Normalize → Concat → Audio Overlay → Subtitle Burn
    │
    ▼
[output/final_video.mp4]
    │
    ▼
[Publisher] ──no-op hook──► (future: YouTube upload)
```

## Provider Architecture

All providers implement a Protocol interface:

- **TTSProvider**: `synthesize(text, locale, output_path) -> AudioResult`
- **VideoGenProvider**: `generate(prompt, duration, output_path) -> VideoResult`
- **Publisher**: `publish(video_path, metadata) -> None`

Factory functions (`create_tts_provider`, `create_video_provider`) select the
implementation based on config. Adding a new provider = one new file + one
factory entry.

## Checkpoint/Resume

TaskState is persisted to `output/.tmp/task_state.json` after each scene.
On `--resume`, the pipeline skips already-completed scenes and continues
from the last checkpoint.

## Free-Tier Design

Default configuration uses only free tools:
- Rule-based scene parsing (no LLM API)
- edge-tts (no API key)
- Mock video provider (FFmpeg synthetic)
- FFmpeg (open-source)

Optional upgrades: Ollama/OpenAI/Anthropic for LLM, real video gen via
Hugging Face/Replicate/FAL, Kokoro-82M for local TTS.

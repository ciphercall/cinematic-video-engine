"""Configuration loading — environment variables and .env support."""

import os
from pathlib import Path
from dataclasses import dataclass, field

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*args, **kwargs):
        pass


@dataclass
class Config:
    """Application configuration."""

    # LLM
    llm_provider: str = "rule_based"  # rule_based | ollama | openai | anthropic | agnes
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-20250514"
    ollama_base_url: str = "http://localhost:11434/v1"
    ollama_model: str = "llama3.2"
    agnes_base_url: str = "https://api.agnes.ai/v1"

    # Video gen
    video_provider: str = "mock"  # mock | stock | docker | wan | hunyuan | ltx
    docker_video_url: str = "http://localhost:8188"

    # TTS
    edge_tts_voice: str = "en-US-GuyNeural"
    kokoro_model_path: str = ""

    # Video gen (free cloud APIs)
    hf_api_token: str = ""  # Hugging Face (free tier)
    replicate_api_token: str = ""  # Replicate (free credits)
    fal_api_key: str = ""  # FAL.ai (free credits)

    # FFmpeg
    ffmpeg_path: str = "ffmpeg"  # or full path
    ffprobe_path: str = "ffprobe"

    # Output
    output_dir: str = "output"
    temp_dir: str = "output/.tmp"

    # Logging
    log_level: str = "INFO"

    # Subtitle styling
    subtitle_font: str = "Arial"
    subtitle_font_size: int = 24
    subtitle_color: str = "FFFFFF"
    subtitle_outline_color: str = "000000"
    subtitle_outline_width: int = 2


def load_config(env_file: str = ".env") -> Config:
    """Load configuration from environment variables and optional .env file."""
    env_path = Path(env_file)
    if env_path.exists():
        load_dotenv(env_path)

    return Config(
        llm_provider=os.getenv("LLM_PROVIDER", "rule_based"),
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        openai_base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4o"),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
        anthropic_model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514"),
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
        ollama_model=os.getenv("OLLAMA_MODEL", "llama3.2"),
        agnes_base_url=os.getenv("AGNES_BASE_URL", "https://api.agnes.ai/v1"),
        video_provider=os.getenv("VIDEO_PROVIDER", "mock"),
        docker_video_url=os.getenv("DOCKER_VIDEO_URL", "http://localhost:8188"),
        edge_tts_voice=os.getenv("EDGE_TTS_VOICE", "en-US-GuyNeural"),
        kokoro_model_path=os.getenv("KOKORO_MODEL_PATH", ""),
        hf_api_token=os.getenv("HF_API_TOKEN", ""),
        replicate_api_token=os.getenv("REPLICATE_API_TOKEN", ""),
        fal_api_key=os.getenv("FAL_API_KEY", ""),
        ffmpeg_path=os.getenv("FFMPEG_PATH", "ffmpeg"),
        ffprobe_path=os.getenv("FFPROBE_PATH", "ffprobe"),
        output_dir=os.getenv("OUTPUT_DIR", "output"),
        temp_dir=os.getenv("TEMP_DIR", "output/.tmp"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        subtitle_font=os.getenv("SUBTITLE_FONT", "Arial"),
        subtitle_font_size=int(os.getenv("SUBTITLE_FONT_SIZE", "24")),
        subtitle_color=os.getenv("SUBTITLE_COLOR", "FFFFFF"),
        subtitle_outline_color=os.getenv("SUBTITLE_OUTLINE_COLOR", "000000"),
        subtitle_outline_width=int(os.getenv("SUBTITLE_OUTLINE_WIDTH", "2")),
    )

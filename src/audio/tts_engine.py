"""TTS engine — provider protocol, factory, and audio result types."""

from typing import Protocol, runtime_checkable
from pathlib import Path
from src.models.scene import AudioResult
from src.config import Config


@runtime_checkable
class TTSProvider(Protocol):
    """Protocol for TTS providers."""

    async def synthesize(self, text: str, locale: str, output_path: Path) -> AudioResult: ...
    async def list_voices(self, locale: str) -> list[str]: ...


def create_tts_provider(provider_name: str, config: Config) -> TTSProvider:
    """Factory: create a TTS provider by name."""
    if provider_name == "edge":
        from src.audio.edge_tts_provider import EdgeTTSProvider
        return EdgeTTSProvider(config)
    elif provider_name == "kokoro":
        from src.audio.kokoro_provider import KokoroProvider
        return KokoroProvider(config)
    else:
        raise ValueError(f"Unknown TTS provider: {provider_name}")

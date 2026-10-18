"""Video generation client — pluggable provider protocol and factory."""

from typing import Protocol, runtime_checkable
from pathlib import Path
from src.models.scene import VideoResult
from src.config import Config


@runtime_checkable
class VideoGenProvider(Protocol):
    """Protocol for video generation providers."""

    async def generate(self, prompt: str, duration_seconds: float, output_path: Path) -> VideoResult: ...


def create_video_provider(provider_name: str, config: Config) -> VideoGenProvider:
    """Factory: create a video gen provider by name."""
    if provider_name == "mock":
        from src.video.mock_provider import MockVideoProvider
        return MockVideoProvider(config)
    elif provider_name == "wan":
        from src.video.wan_provider import WanProvider
        return WanProvider(config)
    elif provider_name == "hunyuan":
        from src.video.hunyuan_provider import HunyuanProvider
        return HunyuanProvider(config)
    elif provider_name == "ltx":
        from src.video.ltx_provider import LTXProvider
        return LTXProvider(config)
    else:
        raise ValueError(f"Unknown video provider: {provider_name}")

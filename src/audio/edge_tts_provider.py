"""Edge TTS provider — Microsoft Edge TTS via edge-tts library."""

import asyncio
from pathlib import Path
from src.models.scene import AudioResult
from src.config import Config

# Language → default voice mapping
DEFAULT_VOICES = {
    "en": "en-US-GuyNeural",
    "bn": "bn-BD-PradeepNeural",
    "es": "es-ES-AlvaroNeural",
    "fr": "fr-FR-HenriNeural",
    "de": "de-DE-ConradNeural",
    "ja": "ja-JP-KeitaNeural",
    "zh": "zh-CN-YunxiNeural",
    "ko": "ko-KR-InJoonNeural",
    "hi": "hi-IN-MadhurNeural",
    "ar": "ar-SA-HamedNeural",
    "pt": "pt-BR-AntonioNeural",
    "ru": "ru-RU-DmitryNeural",
    "it": "it-IT-DiegoNeural",
}


class EdgeTTSProvider:
    """TTS provider using Microsoft Edge TTS (free, uncapped)."""

    def __init__(self, config: Config):
        self.config = config

    def _get_voice(self, locale: str) -> str:
        if self.config.edge_tts_voice and self.config.edge_tts_voice != "en-US-GuyNeural":
            return self.config.edge_tts_voice
        lang = locale.split("-")[0].lower()
        return DEFAULT_VOICES.get(lang, "en-US-GuyNeural")

    async def synthesize(self, text: str, locale: str, output_path: Path) -> AudioResult:
        """Synthesize speech and extract word-level timings."""
        import edge_tts

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        voice = self._get_voice(locale)
        communicate = edge_tts.Communicate(text, voice)

        word_timings = []
        audio_data = bytearray()

        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data.extend(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                word_timings.append({
                    "word": chunk["text"],
                    "start_ms": chunk["offset"] // 10000,  # 100ns → ms
                    "end_ms": (chunk["offset"] + chunk["duration"]) // 10000,
                })

        # Write audio file
        output_path.write_bytes(audio_data)

        # Get duration via file probe
        from src.utils.ffmpeg import probe_duration
        duration_ms = int(await probe_duration(str(output_path), self.config.ffprobe_path) * 1000)

        return AudioResult(
            file=str(output_path),
            duration_ms=duration_ms,
            word_timings=word_timings,
            provider="edge-tts",
        )

    async def list_voices(self, locale: str) -> list[str]:
        import edge_tts
        voices = await edge_tts.list_voices()
        lang = locale.split("-")[0].lower()
        return [v["ShortName"] for v in voices if v["Locale"].lower().startswith(lang)]

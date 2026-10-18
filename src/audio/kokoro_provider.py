"""Kokoro-82M TTS provider — local open-weights TTS (optional)."""

from pathlib import Path
from src.models.scene import AudioResult
from src.config import Config


class KokoroProvider:
    """TTS provider using Kokoro-82M (local inference, open-weights).

    Requires: pip install kokoro soundfile
    Model weights downloaded on first use (~300MB).
    """

    def __init__(self, config: Config):
        self.config = config
        self._pipeline = None

    def _get_pipeline(self):
        if self._pipeline is None:
            try:
                from kokoro import KPipeline
            except ImportError:
                raise RuntimeError(
                    "Kokoro not installed. Run: pip install kokoro soundfile"
                )
            lang_code = "a"  # American English default
            self._pipeline = KPipeline(lang_code=lang_code)
        return self._pipeline

    async def synthesize(self, text: str, locale: str, output_path: Path) -> AudioResult:
        """Synthesize speech using Kokoro-82M (runs in thread to avoid blocking)."""
        import asyncio

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        def _run():
            pipeline = self._get_pipeline()
            # Kokoro generates audio as numpy array
            generator = pipeline(text, voice="af_heart", speed=1.0)
            import soundfile as sf
            import numpy as np
            audio_chunks = []
            for _, _, audio in generator:
                audio_chunks.append(audio)
            if audio_chunks:
                audio = np.concatenate(audio_chunks)
            else:
                audio = np.array([])
            sf.write(str(output_path), audio, 24000)
            duration_ms = int(len(audio) / 24000 * 1000)
            return duration_ms

        duration_ms = await asyncio.get_event_loop().run_in_executor(None, _run)

        # Kokoro doesn't provide word-level timings; estimate from duration
        words = text.split()
        word_duration = duration_ms / max(len(words), 1)
        word_timings = [
            {"word": w, "start_ms": int(i * word_duration), "end_ms": int((i + 1) * word_duration)}
            for i, w in enumerate(words)
        ]

        return AudioResult(
            file=str(output_path),
            duration_ms=duration_ms,
            word_timings=word_timings,
            provider="kokoro-82m",
        )

    async def list_voices(self, locale: str) -> list[str]:
        # Kokoro voices: af_heart, af_bella, am_adam, etc.
        return ["af_heart", "af_bella", "am_adam", "am_michael", "bf_emma", "bm_george"]

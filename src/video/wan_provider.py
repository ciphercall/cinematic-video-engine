"""Wan2.1/3.0 video generation provider — free cloud API via Hugging Face."""

import asyncio
from pathlib import Path
from src.models.scene import VideoResult
from src.config import Config
from src.video.cloud_api_wrapper import CloudAPIWrapper
from src.utils.logger import setup_logger


class WanProvider:
    """Video generation via Wan2.1/3.0 (open-weights, free cloud API).

    Uses Hugging Face Inference API (free tier) or Replicate (free credits).
    Model: Wan-AI/Wan2.1-T2V-14B or Wan2.1-T2V-1.3B for lighter inference.
    """

    def __init__(self, config: Config):
        self.config = config
        self.logger = setup_logger(config.log_level)
        self.api = CloudAPIWrapper(self.logger)

    async def generate(self, prompt: str, duration_seconds: float, output_path: Path) -> VideoResult:
        """Generate a video clip from a text prompt."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Try Hugging Face Inference API first (free tier)
        if self.config.hf_api_token:
            return await self._generate_hf(prompt, duration_seconds, output_path)

        # Fallback: Replicate (free credits)
        if self.config.replicate_api_token:
            return await self._generate_replicate(prompt, duration_seconds, output_path)

        raise RuntimeError(
            "No video gen API key configured. Set HF_API_TOKEN or REPLICATE_API_TOKEN in .env. "
            "Hugging Face free tier: https://huggingface.co/settings/tokens"
        )

    async def _generate_hf(self, prompt: str, duration_seconds: float, output_path: Path) -> VideoResult:
        """Generate via Hugging Face Inference API."""
        model_id = "Wan-AI/Wan2.1-T2V-14B"
        url = f"https://api-inference.huggingface.co/models/{model_id}"
        headers = {"Authorization": f"Bearer {self.config.hf_api_token}"}
        body = {"inputs": prompt, "parameters": {"num_frames": int(duration_seconds * 16)}}

        self.logger.info(f"Wan: generating video via HF ({model_id})")
        result = await self.api.post(url, headers, body)

        # HF returns a URL or binary; handle both
        if isinstance(result, dict) and "url" in result:
            await self.api.download_file(result["url"], output_path)
        elif isinstance(result, bytes):
            output_path.write_bytes(result)
        else:
            raise RuntimeError(f"Unexpected HF response: {type(result)}")

        duration_ms = int(duration_seconds * 1000)
        return VideoResult(file=str(output_path), duration_ms=duration_ms, provider="wan-hf")

    async def _generate_replicate(self, prompt: str, duration_seconds: float, output_path: Path) -> VideoResult:
        """Generate via Replicate API."""
        import replicate
        self.logger.info("Wan: generating video via Replicate")
        # Replicate runs synchronously; wrap in executor
        import asyncio
        loop = asyncio.get_event_loop()
        prediction = await loop.run_in_executor(
            None,
            lambda: replicate.run(
                "wan-video/wan-2.1-t2v-14b",
                input={"prompt": prompt, "num_frames": int(duration_seconds * 16)},
            ),
        )
        video_url = prediction if isinstance(prediction, str) else prediction[0]
        await self.api.download_file(video_url, output_path, headers={"Authorization": f"Token {self.config.replicate_api_token}"})

        duration_ms = int(duration_seconds * 1000)
        return VideoResult(file=str(output_path), duration_ms=duration_ms, provider="wan-replicate")

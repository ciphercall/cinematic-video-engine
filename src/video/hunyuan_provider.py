"""HunyuanVideo generation provider — free cloud API via Hugging Face Spaces."""

from pathlib import Path
from src.models.scene import VideoResult
from src.config import Config
from src.video.cloud_api_wrapper import CloudAPIWrapper
from src.utils.logger import setup_logger


class HunyuanProvider:
    """Video generation via HunyuanVideo (open-weights, free cloud API).

    Uses Hugging Face Spaces or Inference API (free tier).
    Model: tencent/HunyuanVideo
    """

    def __init__(self, config: Config):
        self.config = config
        self.logger = setup_logger(config.log_level)
        self.api = CloudAPIWrapper(self.logger)

    async def generate(self, prompt: str, duration_seconds: float, output_path: Path) -> VideoResult:
        """Generate a video clip from a text prompt."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if not self.config.hf_api_token:
            raise RuntimeError(
                "HF_API_TOKEN required for HunyuanVideo. Set in .env. "
                "Free tier: https://huggingface.co/settings/tokens"
            )

        model_id = "tencent/HunyuanVideo"
        url = f"https://api-inference.huggingface.co/models/{model_id}"
        headers = {"Authorization": f"Bearer {self.config.hf_api_token}"}
        body = {"inputs": prompt}

        self.logger.info(f"Hunyuan: generating video via HF ({model_id})")
        result = await self.api.post(url, headers, body)

        if isinstance(result, dict) and "url" in result:
            await self.api.download_file(result["url"], output_path)
        elif isinstance(result, bytes):
            output_path.write_bytes(result)
        else:
            raise RuntimeError(f"Unexpected HF response: {type(result)}")

        duration_ms = int(duration_seconds * 1000)
        return VideoResult(file=str(output_path), duration_ms=duration_ms, provider="hunyuan-hf")

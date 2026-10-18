"""Pre-download model weights for the video generation container."""

import os
from huggingface_hub import snapshot_download

MODEL_ID = os.getenv("MODEL_ID", "THUDM/CogVideoX-2b")
CACHE_DIR = os.getenv("HF_HOME", "/app/models")

print(f"Downloading model: {MODEL_ID}")
print(f"Cache dir: {CACHE_DIR}")

snapshot_download(
    repo_id=MODEL_ID,
    cache_dir=CACHE_DIR,
    ignore_patterns=["*.bin"],  # prefer safetensors
)

print("Model download complete!")
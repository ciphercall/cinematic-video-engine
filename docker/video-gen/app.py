"""FastAPI server for local video generation using CogVideoX-2B.

Runs inside Docker. Exposes POST /generate endpoint.
"""

import os
import io
import base64
import tempfile
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
import torch
from diffusers import CogVideoXPipeline
import imageio

app = FastAPI(title="Local Video Gen", version="1.0")

MODEL_ID = os.getenv("MODEL_ID", "THUDM/CogVideoX-2b")
DEVICE = os.getenv("DEVICE", "cpu")
TORCH_DTYPE = os.getenv("TORCH_DTYPE", "float32")

pipe = None


class GenerateRequest(BaseModel):
    prompt: str
    num_frames: int = 49  # ~6s at 8fps
    num_inference_steps: int = 50
    guidance_scale: float = 6.0
    height: int = 480
    width: int = 720


class GenerateResponse(BaseModel):
    status: str
    file: str
    duration_ms: int


@app.on_event("startup")
async def load_model():
    global pipe
    try:
        dtype = torch.float32 if TORCH_DTYPE == "float32" else torch.float16
        pipe = CogVideoXPipeline.from_pretrained(
            MODEL_ID,
            torch_dtype=dtype,
        )
        if DEVICE == "cpu":
            pipe.enable_model_cpu_offload()
        print(f"Model loaded: {MODEL_ID} on {DEVICE}")
    except Exception as e:
        print(f"Failed to load model: {e}")
        pipe = None


@app.get("/health")
async def health():
    if pipe is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    return {"status": "ok", "model": MODEL_ID, "device": DEVICE}


@app.post("/generate", response_model=GenerateResponse)
async def generate(req: GenerateRequest):
    if pipe is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    try:
        # Generate video
        result = pipe(
            prompt=req.prompt,
            num_videos_per_prompt=1,
            num_inference_steps=req.num_inference_steps,
            num_frames=req.num_frames,
            guidance_scale=req.guidance_scale,
            height=req.height,
            width=req.width,
        )
        frames = result.frames[0]

        # Save to temp file
        output_dir = Path("/app/output")
        output_dir.mkdir(exist_ok=True)
        import uuid
        filename = f"video_{uuid.uuid4().hex[:8]}.mp4"
        output_path = output_dir / filename

        # Write frames as MP4
        writer = imageio.get_writer(str(output_path), fps=8, codec="libx264", quality=8)
        for frame in frames:
            writer.append_data(frame)
        writer.close()

        duration_ms = int(req.num_frames / 8 * 1000)
        return GenerateResponse(status="ok", file=filename, duration_ms=duration_ms)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/video/{filename}")
async def get_video(filename: str):
    path = Path("/app/output") / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Video not found")
    return FileResponse(path, media_type="video/mp4")
# Use pre-built PyTorch image (already has torch installed, saves ~779MB download)
FROM pytorch/pytorch:2.3.1-cpu

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install remaining Python dependencies
RUN pip install --no-cache-dir \
    diffusers==0.30.0 \
    transformers==4.44.0 \
    accelerate==0.33.0 \
    fastapi==0.112.0 \
    uvicorn==0.30.0 \
    imageio==2.34.0 \
    imageio-ffmpeg==0.5.1 \
    safetensors==0.4.3 \
    sentencepiece==0.2.0 \
    protobuf==4.25.3 \
    huggingface_hub

# Copy application code
COPY app.py download_model.py ./

# Expose port
EXPOSE 8188

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=300s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8188/health')" || exit 1

# Run the server
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8188"]
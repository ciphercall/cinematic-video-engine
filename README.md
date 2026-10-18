# Cinematic Video Engine

Convert raw, researched text documents into cinema-quality widescreen (16:9) narrative videos with synchronized voiceovers.

## Features

- **Text → Scenes**: LLM-powered or rule-based parsing of raw text into chronological semantic scenes
- **Cinematic Prompts**: Auto-enhanced visual prompts with camera angles, panning, lighting, and cinematic style
- **Multi-language TTS**: edge-tts (40+ languages, free, uncapped) or Kokoro-82M (local, open-weights)
- **Pluggable Video Gen**: Mock (FFmpeg synthetic), Wan2.1, HunyuanVideo, LTX-Video via free cloud APIs
- **FFmpeg Assembly**: Clip normalization, concatenation, audio overlay, word-by-word subtitle burning
- **Publishing Hook**: Clean interface for future YouTube/publishing module integration
- **Checkpoint/Resume**: Long runs can resume from last completed scene
- **Dry Run**: Preview scene plan without generating

## Quick Start (No API Keys Needed)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure (defaults work out of the box)
cp .env.example .env
# Edit FFmpeg paths if needed (see .env)

# 3. Check system
python -m src.main doctor

# 4. Test TTS
python -m src.main tts-smoke --locale en-US

# 5. Generate video (uses mock video + rule-based scene parsing)
python -m src.main generate input/sample.txt -o output/

# 6. Verify output
ffprobe output/final_video.mp4
```

## CLI Reference

```bash
# Generate video
python -m src.main generate <input.txt> -o <output_dir>
  --tts edge|kokoro          TTS provider (default: edge)
  --video mock|wan|hunyuan|ltx  Video gen provider (default: from .env)
  --language en              Language code
  --max-scenes N             Max number of scenes
  --subtitles                Burn word-by-word subtitles (default: on)
  --resume                   Resume from last checkpoint
  --dry-run                  Preview plan without generating

# Check system
python -m src.main doctor

# Test TTS
python -m src.main tts-smoke --locale en-US --text "Hello world"
```

## Free-Tier Tool Stack (No Paid Subscriptions)

| Component | Default Tool | Cost | Upgrade Option |
|-----------|-------------|------|----------------|
| LLM (scene parsing) | Rule-based | Free | Ollama (local) or OpenAI/Anthropic |
| TTS (voiceover) | edge-tts | Free, uncapped | Kokoro-82M (local) |
| Video gen | Mock (FFmpeg) | Free | Wan/Hunyuan/LTX via HF/Replicate/FAL |
| Assembly | FFmpeg | Free, open-source | — |
| Subtitles | ASS (manual) | Free | — |

## Upgrading to Real Video Generation

### Option A: Free Cloud API (Hugging Face)
1. Get a free Hugging Face token: https://huggingface.co/settings/tokens
2. Set `HF_API_TOKEN=hf_...` in `.env`
3. Set `VIDEO_PROVIDER=wan` in `.env` (or pass `--video wan`)
4. Run: `python -m src.main generate input/sample.txt -o output/ --video wan`

### Option B: Local Docker (Completely Free, No API Keys)
Requires Docker Desktop and 12GB+ RAM. Runs CogVideoX-2B on CPU.

1. Start the Docker container:
   ```bash
   docker compose -f docker/docker-compose.yml up -d
   ```
   (First run downloads ~5GB model weights — takes a few minutes)

2. Wait for health check:
   ```bash
   curl http://localhost:8188/health
   ```

3. Set `VIDEO_PROVIDER=docker` in `.env` (or pass `--video docker`)

4. Run:
   ```bash
   python -m src.main generate input/sample.txt -o output/ --video docker
   ```

**Note**: CPU inference is slow (~5-10 min per 6s clip). For faster generation, use Option A.

## Upgrading to LLM Scene Parsing

1. Install Ollama: https://ollama.com
2. Run: `ollama pull llama3.2`
3. Set `LLM_PROVIDER=ollama` in `.env`
4. Run: `python -m src.main generate input/sample.txt -o output/`

## Architecture

```
src/
├── agents/          # Text processing (scene parser, prompt builder, LLM clients)
├── audio/           # Audio generation (TTS providers, subtitles)
├── video/           # Video generation (mock, wan, hunyuan, ltx providers)
├── compiler/        # Video assembly engine (FFmpeg)
├── pipelines/       # Orchestration (narrative pipeline)
├── publishers/      # Future publishing module slot
├── models/          # Data models (Scene, TaskState)
└── utils/           # Shared utilities (FFmpeg, logging, doctor)
```

## Requirements

- Python 3.10+
- FFmpeg (on PATH or set FFMPEG_PATH/FFPROBE_PATH in .env)

## License

MIT

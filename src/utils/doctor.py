"""Doctor — check system dependencies and configuration."""

import shutil
import sys
from pathlib import Path
from src.config import load_config
from src.utils.ffmpeg import resolve_ffmpeg


async def run_doctor():
    """Check all system dependencies and API keys."""
    config = load_config()
    required_checks = []
    optional_checks = []

    # Python version (required)
    py_ver = sys.version_info
    required_checks.append(("Python >= 3.10", py_ver >= (3, 10), f"{py_ver.major}.{py_ver.minor}.{py_ver.micro}"))

    # FFmpeg (required)
    try:
        ffmpeg = await resolve_ffmpeg(config.ffmpeg_path)
        required_checks.append(("FFmpeg", True, ffmpeg))
    except Exception as e:
        required_checks.append(("FFmpeg", False, str(e)))

    # ffprobe (required)
    ffprobe = shutil.which(config.ffprobe_path) if config.ffprobe_path != "ffprobe" else shutil.which("ffprobe")
    if ffprobe is None and Path(config.ffprobe_path).exists():
        ffprobe = config.ffprobe_path
    required_checks.append(("ffprobe", ffprobe is not None, ffprobe or "not found"))

    # edge-tts (optional)
    try:
        import edge_tts
        optional_checks.append(("edge-tts", True, "installed"))
    except ImportError:
        optional_checks.append(("edge-tts", False, "not installed (pip install edge-tts)"))

    # openai SDK (optional)
    try:
        import openai
        optional_checks.append(("openai SDK", True, "installed"))
    except ImportError:
        optional_checks.append(("openai SDK", False, "not installed"))

    # anthropic SDK (optional)
    try:
        import anthropic
        optional_checks.append(("anthropic SDK", True, "installed"))
    except ImportError:
        optional_checks.append(("anthropic SDK", False, "not installed"))

    # API keys (optional)
    optional_checks.append(("OPENAI_API_KEY", bool(config.openai_api_key), "set" if config.openai_api_key else "missing (optional)"))
    optional_checks.append(("HF_API_TOKEN", bool(config.hf_api_token), "set" if config.hf_api_token else "missing (optional, needed for cloud video gen)"))
    optional_checks.append(("ANTHROPIC_API_KEY", bool(config.anthropic_api_key), "set" if config.anthropic_api_key else "missing (optional)"))

    # Print results
    print("\n=== Doctor ===")
    print("\nRequired:")
    all_required_ok = True
    for name, ok, detail in required_checks:
        status = "[OK]" if ok else "[FAIL]"
        if not ok:
            all_required_ok = False
        print(f"  {status} {name}: {detail}")

    print("\nOptional:")
    for name, ok, detail in optional_checks:
        status = "[OK]" if ok else "[--]"
        print(f"  {status} {name}: {detail}")

    if all_required_ok:
        print("\nAll required checks passed! Optional items can be installed/configured as needed.")
    else:
        print("\nSome required checks failed. See above.")
        sys.exit(1)

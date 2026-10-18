#!/usr/bin/env python3
"""Cinematic Video Engine — convert text documents into cinema-quality 16:9 videos."""

import argparse
import asyncio
from pathlib import Path

from src.config import load_config
from src.utils.logger import setup_logger
from src.pipelines.narrative_pipeline import NarrativePipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cinema",
        description="Convert researched text documents into cinema-quality 16:9 narrative videos.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # generate
    gen = sub.add_parser("generate", help="Generate video from a text document")
    gen.add_argument("input", type=Path, help="Input text document path")
    gen.add_argument("-o", "--output", type=Path, default=Path("output"), help="Output directory")
    gen.add_argument("--tts", choices=["edge", "kokoro"], default="edge", help="TTS provider")
    gen.add_argument("--video", choices=["mock", "wan", "hunyuan", "ltx"], default=None, help="Video gen provider (default: from .env)")
    gen.add_argument("--language", default="en", help="Language code (e.g. en, bn, es)")
    gen.add_argument("--max-scenes", type=int, default=None, help="Max number of scenes")
    gen.add_argument("--subtitles", action="store_true", default=True, help="Burn word-by-word subtitles")
    gen.add_argument("--resume", action="store_true", default=False, help="Resume from last checkpoint")
    gen.add_argument("--dry-run", action="store_true", default=False, help="Preview plan without generating")

    # doctor
    sub.add_parser("doctor", help="Check system dependencies and API keys")

    # tts-smoke
    smoke = sub.add_parser("tts-smoke", help="Test TTS synthesis")
    smoke.add_argument("--locale", default="en-US", help="Locale to test")
    smoke.add_argument("--text", default="Welcome to the cinematic video engine.", help="Text to synthesize")
    smoke.add_argument("--provider", choices=["edge", "kokoro"], default="edge", help="TTS provider")

    return parser


async def cmd_generate(args):
    config = load_config()
    logger = setup_logger(config.log_level)

    # Dry run: parse and preview without generating
    if args.dry_run:
        from src.agents.scene_parser import SceneParser
        from src.agents.prompt_builder import PromptBuilder
        from src.agents.llm_client import create_llm_client
        text = args.input.read_text(encoding="utf-8")
        llm = create_llm_client(config)
        parser = SceneParser(llm, config)
        scenes = await parser.parse(text, args.language, args.max_scenes)
        builder = PromptBuilder()
        scenes = builder.enhance_all(scenes)
        print(f"\n=== Dry Run ===")
        print(f"Scenes: {len(scenes)}")
        print(f"Language: {args.language}")
        print(f"TTS: {args.tts}")
        print(f"Video: {args.video or config.video_provider}")
        print(f"Subtitles: {args.subtitles}")
        print()
        for s in scenes:
            print(f"--- Scene {s.index + 1}: {s.id} ---")
            print(f"Narration: {s.narration_text}")
            print(f"Visual: {s.visual_prompt}")
            print()
        return

    pipeline = NarrativePipeline(config, logger)
    output_path = await pipeline.run(
        input_file=args.input,
        output_dir=args.output,
        tts_provider=args.tts,
        video_provider=args.video,
        language=args.language,
        max_scenes=args.max_scenes,
        subtitles=args.subtitles,
        resume=args.resume,
    )
    print(f"\nVideo generated: {output_path}")


async def cmd_doctor(args):
    from src.utils.doctor import run_doctor
    await run_doctor()


async def cmd_tts_smoke(args):
    from src.audio.tts_engine import create_tts_provider
    config = load_config()
    logger = setup_logger(config.log_level)
    provider = create_tts_provider(args.provider, config)
    out_path = Path("output") / "tts_smoke.mp3"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    result = await provider.synthesize(args.text, args.locale, out_path)
    print(f"TTS smoke: {result.file} ({result.duration_ms}ms, provider={result.provider})")


def main():
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "generate":
        asyncio.run(cmd_generate(args))
    elif args.command == "doctor":
        asyncio.run(cmd_doctor(args))
    elif args.command == "tts-smoke":
        asyncio.run(cmd_tts_smoke(args))


if __name__ == "__main__":
    main()

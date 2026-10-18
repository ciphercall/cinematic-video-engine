"""Narrative pipeline — orchestrate the full text-to-video workflow."""

import asyncio
from pathlib import Path
from typing import Optional
from src.models.scene import Scene
from src.models.task import TaskState
from src.agents.scene_parser import SceneParser
from src.agents.prompt_builder import PromptBuilder
from src.agents.llm_client import create_llm_client
from src.audio.tts_engine import create_tts_provider
from src.video.video_client import create_video_provider
from src.compiler.assembler import assemble
from src.publishers.base import NoOpPublisher
from src.config import Config
from src.utils.logger import setup_logger
from src.utils.file_manager import ensure_dir
import json


class NarrativePipeline:
    """Main pipeline: parse text → generate audio + video per scene → compile → publish hook."""

    def __init__(self, config: Config, logger=None):
        self.config = config
        self.logger = logger or setup_logger(config.log_level)
        self.llm = create_llm_client(config)
        self.scene_parser = SceneParser(self.llm, config)
        self.prompt_builder = PromptBuilder()

    async def run(
        self,
        input_file: Path,
        output_dir: Path,
        tts_provider: str = "edge",
        video_provider: str = None,
        language: str = "en",
        max_scenes: Optional[int] = None,
        subtitles: bool = True,
        resume: bool = False,
    ) -> Path:
        """Run the full pipeline and return path to final video."""
        input_file = Path(input_file)
        output_dir = Path(output_dir)
        ensure_dir(output_dir)

        if video_provider is None:
            video_provider = self.config.video_provider

        self.logger.info(f"Reading input: {input_file}")
        text = input_file.read_text(encoding="utf-8")

        # 1. Parse scenes
        self.logger.info("Parsing text into scenes...")
        scenes = await self.scene_parser.parse(text, language, max_scenes)
        self.logger.info(f"Parsed {len(scenes)} scenes")

        # 2. Enhance prompts
        self.logger.info("Enhancing visual prompts with cinematic directives...")
        scenes = self.prompt_builder.enhance_all(scenes)

        # 3. Create providers
        tts = create_tts_provider(tts_provider, self.config)
        video = create_video_provider(video_provider, self.config)

        # 4. Generate audio + video per scene
        tmp_dir = output_dir / ".tmp"
        ensure_dir(tmp_dir)

        # Task state for checkpoint/resume
        from src.models.task import TaskState
        task_state = TaskState(
            task_id=f"run_{input_file.stem}",
            input_file=str(input_file),
            output_dir=str(output_dir),
            language=language,
            tts_provider=tts_provider,
            video_provider=video_provider,
            scenes=[{"id": s.id, "audio_done": False, "video_done": False} for s in scenes],
        )
        state_path = tmp_dir / "task_state.json"

        # Resume from checkpoint if available
        if resume and state_path.exists():
            import json
            saved = json.loads(state_path.read_text())
            task_state = TaskState(**{k: v for k, v in saved.items() if k in TaskState.__dataclass_fields__})
            self.logger.info(f"Resuming from scene {task_state.current_scene_index}")

        for i, scene in enumerate(scenes):
            # Skip already-completed scenes on resume
            if i < task_state.current_scene_index:
                scene.audio_done = task_state.scenes[i].get("audio_done", False)
                scene.video_done = task_state.scenes[i].get("video_done", False)
                if scene.audio_done:
                    scene.audio_file = task_state.scenes[i].get("audio_file")
                    scene.audio_duration_ms = task_state.scenes[i].get("audio_duration_ms", 0)
                    scene.word_timings = task_state.scenes[i].get("word_timings", [])
                if scene.video_done:
                    scene.video_file = task_state.scenes[i].get("video_file")
                    scene.video_duration_ms = task_state.scenes[i].get("video_duration_ms", 0)
                self.logger.info(f"Skipping completed scene {i + 1}/{len(scenes)}: {scene.id}")
                continue

            self.logger.info(f"Processing scene {i + 1}/{len(scenes)}: {scene.id}")

            audio_path = tmp_dir / f"audio_{scene.id}.mp3"
            video_path = tmp_dir / f"video_{scene.id}.mp4"

            # Run audio and video generation concurrently
            try:
                audio_result, video_result = await asyncio.gather(
                    tts.synthesize(scene.narration_text, language, audio_path),
                    video.generate(scene.visual_prompt, scene.estimated_duration, video_path),
                )

                scene.audio_file = audio_result.file
                scene.audio_duration_ms = audio_result.duration_ms
                scene.word_timings = audio_result.word_timings
                scene.audio_done = True

                scene.video_file = video_result.file
                scene.video_duration_ms = video_result.duration_ms
                scene.video_done = True

                self.logger.info(
                    f"Scene {scene.id} done: audio={audio_result.duration_ms}ms, "
                    f"video={video_result.duration_ms}ms"
                )
            except Exception as e:
                self.logger.error(f"Scene {scene.id} failed: {e}")
                # Save state and re-raise
                task_state.current_scene_index = i
                import json
                from dataclasses import asdict
                state_path.write_text(json.dumps(asdict(task_state), indent=2, default=str))
                raise

            # Save checkpoint
            task_state.current_scene_index = i + 1
            task_state.scenes[i]["audio_file"] = scene.audio_file
            task_state.scenes[i]["audio_duration_ms"] = scene.audio_duration_ms
            task_state.scenes[i]["word_timings"] = scene.word_timings
            task_state.scenes[i]["audio_done"] = True
            task_state.scenes[i]["video_file"] = scene.video_file
            task_state.scenes[i]["video_duration_ms"] = scene.video_duration_ms
            task_state.scenes[i]["video_done"] = True
            import json
            from dataclasses import asdict
            state_path.write_text(json.dumps(asdict(task_state), indent=2, default=str))

        # 5. Compile
        self.logger.info("Assembling final video...")
        final_path = await assemble(scenes, output_dir, self.config, subtitles)
        self.logger.info(f"Final video: {final_path}")

        # 6. Publish hook (no-op default; future module plugs in here)
        publisher = NoOpPublisher()
        await publisher.publish(final_path, {"scenes": len(scenes), "language": language})

        # Mark complete
        task_state.status = "completed"
        task_state.final_output = str(final_path)
        import json
        from dataclasses import asdict
        state_path.write_text(json.dumps(asdict(task_state), indent=2, default=str))

        return final_path

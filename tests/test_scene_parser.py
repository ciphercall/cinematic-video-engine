"""Tests for scene parser."""

def test_scene_model_creation():
    from src.models.scene import Scene
    scene = Scene(id="scene_000", index=0, narration_text="Hello world.", visual_prompt="A wide shot.")
    assert scene.id == "scene_000"
    assert scene.narration_text == "Hello world."
    assert not scene.audio_done


def test_prompt_builder_enhances():
    from src.agents.prompt_builder import PromptBuilder
    builder = PromptBuilder()
    result = builder.enhance("A forest scene", scene_index=0)
    assert "16:9" in result or "widescreen" in result.lower()
    assert "cinematic" in result.lower()

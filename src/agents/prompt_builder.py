"""Prompt builder — enhance visual prompts with cinematic directives."""

from typing import List
from src.models.scene import Scene

# Base cinematic suffix appended to every visual prompt
CINEMATIC_SUFFIX = (
    "cinematic 16:9 widescreen, professional color grading, film grain, "
    "depth of field, high production value, broadcast quality, 4K resolution"
)

# Motion keywords to ensure non-static output
MOTION_KEYWORDS = [
    "slow camera pan", "gentle dolly movement", "tracking shot",
    "parallax motion", "subtle zoom", "atmospheric drift",
]

# Lighting presets for variety
LIGHTING_PRESETS = [
    "golden hour lighting", "dramatic side lighting", "soft diffused light",
    "neon accent lighting", "natural daylight", "moody backlight",
]


class PromptBuilder:
    """Enhance raw visual prompts with cinematic directives."""

    def __init__(self):
        self._lighting_index = 0

    def enhance(self, prompt: str, scene_index: int = 0) -> str:
        """Enhance a single visual prompt with cinematic directives."""
        # Add motion if not already present
        has_motion = any(kw in prompt.lower() for kw in ["pan", "dolly", "tracking", "zoom", "drift", "movement"])
        if not has_motion:
            motion = MOTION_KEYWORDS[scene_index % len(MOTION_KEYWORDS)]
            prompt = f"{prompt}, {motion}"

        # Add lighting if not already present
        has_lighting = any(kw in prompt.lower() for kw in ["lighting", "golden hour", "dramatic", "soft light"])
        if not has_lighting:
            lighting = LIGHTING_PRESETS[scene_index % len(LIGHTING_PRESETS)]
            prompt = f"{prompt}, {lighting}"

        # Ensure 16:9 framing is mentioned
        if "16:9" not in prompt and "widescreen" not in prompt.lower():
            prompt = f"{prompt}, 16:9 widescreen framing"

        # Append base cinematic suffix
        if CINEMATIC_SUFFIX.split(",")[0] not in prompt.lower():
            prompt = f"{prompt}, {CINEMATIC_SUFFIX}"

        return prompt

    def enhance_all(self, scenes: List[Scene]) -> List[Scene]:
        """Enhance visual prompts for all scenes in place."""
        for scene in scenes:
            scene.visual_prompt = self.enhance(scene.visual_prompt, scene.index)
        return scenes

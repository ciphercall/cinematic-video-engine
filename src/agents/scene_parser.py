"""Scene parser — convert raw researched text into chronological semantic scenes."""

import json
import re
from typing import List
from src.models.scene import Scene
from src.agents.llm_client import LLMClient, create_llm_client
from src.config import Config


SCENE_PARSER_SYSTEM_PROMPT = """You are a cinematic video scriptwriter and scene director.
Your job is to parse raw research text into distinct, chronological semantic scenes for a 16:9 narrative video.

For each scene, output a JSON object with:
- "narration_text": The script to be read aloud (natural, engaging, 2-4 sentences max).
- "visual_prompt": A detailed cinematic description for video generation. MUST include:
  * Camera angle (wide shot, close-up, aerial, tracking, etc.)
  * Camera movement (pan, dolly, tilt, crane, handheld, static with parallax)
  * Lighting (golden hour, dramatic, soft, neon, etc.)
  * Cinematic style (film grain, depth of field, color grading)
  * Subject and action description
  * Must specify 16:9 widescreen framing
  * Must convey MOTION — never describe a static image

Output a JSON array of scene objects. No markdown, no explanation, just the JSON array.
Example:
[
  {
    "narration_text": "In the heart of the Amazon, ancient trees tower above the forest floor.",
    "visual_prompt": "Cinematic 16:9 wide aerial shot slowly descending through misty Amazon canopy, golden hour sunlight filtering through leaves, gentle camera dolly forward, lush green tones, film grain, shallow depth of field, professional color grading, parallax motion between foreground and background layers"
  }
]"""


class SceneParser:
    """Parse raw text into a list of Scene objects using an LLM."""

    def __init__(self, llm_client: LLMClient, config: Config):
        self.llm = llm_client
        self.config = config

    async def parse(self, text: str, language: str = "en", max_scenes: int | None = None) -> List[Scene]:
        """Parse raw text into chronological scenes."""
        user_prompt = f"Language for narration: {language}\n\nRaw research text:\n{text}"
        if max_scenes:
            user_prompt += f"\n\nMaximum scenes: {max_scenes}"

        response = await self.llm.complete(SCENE_PARSER_SYSTEM_PROMPT, user_prompt)

        # Extract JSON from response (handle markdown code blocks)
        json_str = response.strip()
        if json_str.startswith("```"):
            json_str = re.sub(r"^```(?:json)?\s*", "", json_str)
            json_str = re.sub(r"\s*```$", "", json_str)

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError:
            # Try to find JSON array in the response
            match = re.search(r"\[.*\]", json_str, re.DOTALL)
            if match:
                data = json.loads(match.group())
            else:
                raise ValueError(f"LLM did not return valid JSON: {response[:500]}")

        scenes = []
        for i, item in enumerate(data):
            scenes.append(Scene(
                id=f"scene_{i:03d}",
                index=i,
                narration_text=item["narration_text"],
                visual_prompt=item["visual_prompt"],
            ))
        return scenes

"""LLM client abstraction — pluggable text providers (OpenAI / Anthropic / Agnes)."""

import json
from typing import Protocol, Optional
from src.config import Config


class LLMClient(Protocol):
    async def complete(self, system_prompt: str, user_prompt: str, temperature: float = 0.7) -> str: ...


class OpenAIClient:
    """OpenAI-compatible LLM client (also works with any OpenAI-compatible endpoint)."""

    def __init__(self, config: Config):
        self.config = config
        self._client = None

    def _get_client(self):
        if self._client is None:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(
                api_key=self.config.openai_api_key,
                base_url=self.config.openai_base_url,
            )
        return self._client

    async def complete(self, system_prompt: str, user_prompt: str, temperature: float = 0.7) -> str:
        client = self._get_client()
        response = await client.chat.completions.create(
            model=self.config.openai_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
        )
        return response.choices[0].message.content or ""


class AnthropicClient:
    """Anthropic Claude LLM client."""

    def __init__(self, config: Config):
        self.config = config
        self._client = None

    def _get_client(self):
        if self._client is None:
            from anthropic import AsyncAnthropic
            self._client = AsyncAnthropic(api_key=self.config.anthropic_api_key)
        return self._client

    async def complete(self, system_prompt: str, user_prompt: str, temperature: float = 0.7) -> str:
        client = self._get_client()
        response = await client.messages.create(
            model=self.config.anthropic_model,
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
            temperature=temperature,
        )
        return response.content[0].text if response.content else ""


class OllamaClient:
    """Ollama local LLM client (free, OpenAI-compatible API)."""

    def __init__(self, config: Config):
        self.config = config
        self._client = None

    def _get_client(self):
        if self._client is None:
            from openai import AsyncOpenAI
            base_url = getattr(self.config, "ollama_base_url", "http://localhost:11434/v1")
            self._client = AsyncOpenAI(api_key="ollama", base_url=base_url)
        return self._client

    async def complete(self, system_prompt: str, user_prompt: str, temperature: float = 0.7) -> str:
        client = self._get_client()
        model = getattr(self.config, "ollama_model", "llama3.2")
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
        )
        return response.choices[0].message.content or ""


class RuleBasedClient:
    """Rule-based LLM client — no API needed. Splits text into scenes by paragraphs."""

    def __init__(self, config: Config):
        self.config = config

    async def complete(self, system_prompt: str, user_prompt: str, temperature: float = 0.7) -> str:
        # Extract the raw text from user_prompt
        text = user_prompt
        if "Raw research text:" in text:
            text = text.split("Raw research text:")[-1].strip()

        # Split into paragraphs
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        if not paragraphs:
            paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
        if not paragraphs:
            paragraphs = [text.strip()]

        # Build scenes JSON
        scenes = []
        for i, para in enumerate(paragraphs):
            # Truncate very long paragraphs
            if len(para) > 500:
                sentences = para.split(". ")
                chunk = ""
                chunks = []
                for s in sentences:
                    if len(chunk) + len(s) > 400:
                        if chunk:
                            chunks.append(chunk.strip())
                        chunk = s + ". "
                    else:
                        chunk += s + ". "
                if chunk.strip():
                    chunks.append(chunk.strip())
                for c in chunks:
                    scenes.append({"narration_text": c, "visual_prompt": f"Cinematic scene: {c[:100]}"})
            else:
                scenes.append({"narration_text": para, "visual_prompt": f"Cinematic scene: {para[:100]}"})

        import json
        return json.dumps(scenes)


def create_llm_client(config: Config) -> LLMClient:
    """Factory: create the appropriate LLM client based on config."""
    provider = getattr(config, "llm_provider", "openai")
    if provider == "anthropic":
        return AnthropicClient(config)
    elif provider == "ollama":
        return OllamaClient(config)
    elif provider == "rule_based":
        return RuleBasedClient(config)
    elif provider == "agnes":
        # Agnes uses OpenAI-compatible API
        config.openai_base_url = getattr(config, "agnes_base_url", "https://api.agnes.ai/v1")
        return OpenAIClient(config)
    return OpenAIClient(config)

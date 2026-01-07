import os
from pathlib import Path

import anthropic

from .base_provider import BaseLLMProvider


def get_api_key() -> str:
    """Get API key from environment or ~/.anthropic_api_key file."""
    # First check environment variable
    if api_key := os.environ.get("ANTHROPIC_API_KEY"):
        return api_key

    # Then check file in home directory
    key_file = Path.home() / ".anthropic_api_key"
    if key_file.exists():
        return key_file.read_text().strip()

    raise ValueError(
        "ANTHROPIC_API_KEY not found. Set it as an environment variable "
        "or create ~/.anthropic_api_key"
    )


class AnthropicProvider(BaseLLMProvider):
    name = "anthropic"

    def __init__(self, model: str = "claude-sonnet-4-20250514"):
        self._model = model
        self._client = anthropic.Anthropic(api_key=get_api_key())

    def generate_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 4096,
    ) -> str:
        message = self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return message.content[0].text

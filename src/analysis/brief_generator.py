import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from src.storage import MarkdownStore, ContentFile
from .llm import BaseLLMProvider, AnthropicProvider


class BriefGenerator:
    def __init__(
        self,
        store: MarkdownStore,
        system_prompt: str,
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 8000,
        content_window_hours: int = 24,
    ):
        self._store = store
        self._system_prompt = system_prompt
        self._model = model
        self._max_tokens = max_tokens
        self._content_window_hours = content_window_hours
        self._provider: BaseLLMProvider = AnthropicProvider(model=model)

    def generate(self, dry_run: bool = False) -> Optional[Path]:
        now = datetime.utcnow()
        since = now - timedelta(hours=self._content_window_hours)

        content_files = self._store.get_content_since(since)
        if not content_files:
            return None

        ref_map = {}
        user_prompt = self._build_prompt(content_files, ref_map)

        if dry_run:
            print(f"Would analyze {len(content_files)} items")
            print(f"Sources: {set(c.source_id for c in content_files)}")
            return None

        response = self._provider.generate_completion(
            system_prompt=self._system_prompt,
            user_prompt=user_prompt,
            max_tokens=self._max_tokens,
        )

        source_map = self._build_source_map(ref_map)

        brief_path = self._store.store_brief(
            content=response,
            generated_at=now,
            window_from=since,
            window_to=now,
            sources_analyzed=len(content_files),
            model=self._model,
            source_map=source_map,
        )

        return brief_path

    def _build_prompt(
        self, content_files: list[ContentFile], ref_map: dict[str, ContentFile]
    ) -> str:
        lines = ["Here are the articles to analyze:\n"]

        for i, cf in enumerate(content_files, 1):
            ref_id = f"ref{i}"
            ref_map[ref_id] = cf

            lines.append(f"---\n")
            lines.append(f"Reference ID: {ref_id}\n")
            lines.append(f"Title: {cf.title}\n")
            lines.append(f"Source: {cf.source_name}\n")
            lines.append(f"Published: {cf.published_at.strftime('%Y-%m-%d %H:%M')}\n")
            lines.append(f"URL: {cf.url}\n")
            lines.append(f"\n{cf.content[:2000]}\n")

        lines.append("---\n")
        lines.append("\nPlease generate a daily brief based on these articles.")

        return "\n".join(lines)

    def _build_source_map(
        self, ref_map: dict[str, ContentFile]
    ) -> dict[str, str]:
        source_map = {}
        for ref_id, cf in ref_map.items():
            relative_path = cf.file_path.relative_to(cf.file_path.parent.parent.parent)
            source_map[ref_id] = str(relative_path)
        return source_map

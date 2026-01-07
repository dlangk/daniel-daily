from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel

from .types import Source, SourceType


class SourcesConfig(BaseModel):
    sources: list[Source]


class SourceRegistry:
    def __init__(self, config_path: Path):
        self._config_path = config_path
        self._sources: dict[str, Source] = {}
        self._load()

    def _load(self) -> None:
        with open(self._config_path) as f:
            data = yaml.safe_load(f)
        config = SourcesConfig.model_validate(data)
        self._sources = {s.id: s for s in config.sources}

    def get_all_sources(self) -> list[Source]:
        return list(self._sources.values())

    def get_source_by_id(self, source_id: str) -> Optional[Source]:
        return self._sources.get(source_id)

    def get_sources_by_type(self, source_type: SourceType) -> list[Source]:
        return [s for s in self._sources.values() if s.type == source_type]

    def get_enabled_sources(self) -> list[Source]:
        return [s for s in self._sources.values() if s.enabled]

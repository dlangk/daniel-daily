from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from src.curation import Source


@dataclass
class FetchResult:
    id: str
    source_id: str
    title: str
    content: str
    url: str
    published_at: datetime
    fetched_at: datetime
    author: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class FetchOutcome:
    success: bool
    results: list[FetchResult]
    error_message: Optional[str] = None
    error_type: Optional[str] = None


class BaseFetcher(ABC):
    source_type: str

    @abstractmethod
    def fetch(self, source: Source) -> FetchOutcome:
        pass

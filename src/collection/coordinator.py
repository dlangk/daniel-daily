import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from src.curation import Source, SourceRegistry, SourceType
from src.state import SourceStateManager
from src.storage import MarkdownStore, Deduplicator
from .fetchers import BaseFetcher, RSSFetcher, FetchOutcome


@dataclass
class CollectionStats:
    sources_processed: int = 0
    items_fetched: int = 0
    items_stored: int = 0
    items_skipped_duplicate: int = 0
    errors: int = 0


class Coordinator:
    def __init__(
        self,
        source_registry: SourceRegistry,
        state_manager: SourceStateManager,
        store: MarkdownStore,
        deduplicator: Deduplicator,
        max_age_days: int = 7,
    ):
        self._registry = source_registry
        self._state = state_manager
        self._store = store
        self._dedup = deduplicator
        self._max_age_days = max_age_days
        self._fetchers: dict[str, BaseFetcher] = {
            SourceType.RSS.value: RSSFetcher(),
        }

    def collect_all(self, force: bool = False) -> CollectionStats:
        stats = CollectionStats()
        sources = self._registry.get_enabled_sources()

        for source in sources:
            source_stats = self.collect_source(source, force=force)
            stats.sources_processed += 1
            stats.items_fetched += source_stats.items_fetched
            stats.items_stored += source_stats.items_stored
            stats.items_skipped_duplicate += source_stats.items_skipped_duplicate
            stats.errors += source_stats.errors

        return stats

    def collect_source(
        self, source: Source, force: bool = False
    ) -> CollectionStats:
        stats = CollectionStats()
        stats.sources_processed = 1

        fetcher = self._fetchers.get(source.type.value)
        if not fetcher:
            stats.errors = 1
            return stats

        start_time = time.time()
        outcome = fetcher.fetch(source)
        duration = time.time() - start_time

        if not outcome.success:
            self._state.record_failure(
                source.id,
                Exception(outcome.error_message or "Unknown error"),
                duration,
            )
            stats.errors = 1
            return stats

        cutoff = datetime.utcnow() - timedelta(days=self._max_age_days)
        items_stored = 0

        for result in outcome.results:
            stats.items_fetched += 1

            if result.published_at < cutoff:
                continue

            if not force and self._dedup.exists(result.id):
                stats.items_skipped_duplicate += 1
                continue

            source_obj = self._registry.get_source_by_id(result.source_id)
            source_name = source_obj.name if source_obj else result.source_id

            self._store.store_content(
                content_id=result.id,
                source_id=result.source_id,
                source_name=source_name,
                title=result.title,
                url=result.url,
                content=result.content,
                published_at=result.published_at,
                fetched_at=result.fetched_at,
                category=source.category,
                author=result.author,
                metadata=result.metadata,
            )
            self._dedup.add(result.id)
            items_stored += 1
            stats.items_stored += 1

        self._state.record_success(source.id, items_stored, duration)
        return stats

    def collect_by_id(
        self, source_id: str, force: bool = False
    ) -> Optional[CollectionStats]:
        source = self._registry.get_source_by_id(source_id)
        if not source:
            return None
        return self.collect_source(source, force=force)

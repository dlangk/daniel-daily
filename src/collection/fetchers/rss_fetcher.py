from datetime import datetime
from time import mktime
from typing import Optional
import logging

import feedparser
import trafilatura

from src.curation import Source
from .base_fetcher import BaseFetcher, FetchResult, FetchOutcome

logger = logging.getLogger(__name__)


class RSSFetcher(BaseFetcher):
    source_type = "rss"

    def fetch(self, source: Source) -> FetchOutcome:
        try:
            feed = feedparser.parse(source.url)

            if feed.bozo and not feed.entries:
                return FetchOutcome(
                    success=False,
                    results=[],
                    error_message=str(feed.bozo_exception),
                    error_type=type(feed.bozo_exception).__name__,
                )

            results = []
            fetched_at = datetime.utcnow()

            for entry in feed.entries:
                result = self._parse_entry(entry, source, fetched_at)
                if result:
                    results.append(result)

            return FetchOutcome(success=True, results=results)

        except Exception as e:
            return FetchOutcome(
                success=False,
                results=[],
                error_message=str(e),
                error_type=type(e).__name__,
            )

    def _fetch_full_article(self, url: str) -> Optional[str]:
        """Fetch and extract full article text from URL."""
        try:
            downloaded = trafilatura.fetch_url(url)
            if downloaded:
                text = trafilatura.extract(
                    downloaded,
                    include_comments=False,
                    include_tables=True,
                    no_fallback=False,
                )
                return text
        except Exception as e:
            logger.debug(f"Failed to fetch article from {url}: {e}")
        return None

    def _parse_entry(
        self, entry: dict, source: Source, fetched_at: datetime
    ) -> Optional[FetchResult]:
        try:
            entry_id = entry.get("id") or entry.get("link") or entry.get("title")
            if not entry_id:
                return None

            title = entry.get("title", "Untitled")
            url = entry.get("link", "")

            # First try to get content from feed
            content = ""
            if "content" in entry and entry.content:
                content = entry.content[0].get("value", "")
            elif "summary" in entry:
                content = entry.summary
            elif "description" in entry:
                content = entry.description

            # For HN and similar feeds, fetch the actual article
            # If content is short or just contains links, fetch full article
            if url and (len(content) < 500 or "<a href=" in content):
                full_article = self._fetch_full_article(url)
                if full_article and len(full_article) > len(content):
                    content = full_article

            published_at = fetched_at
            if "published_parsed" in entry and entry.published_parsed:
                published_at = datetime.fromtimestamp(mktime(entry.published_parsed))
            elif "updated_parsed" in entry and entry.updated_parsed:
                published_at = datetime.fromtimestamp(mktime(entry.updated_parsed))

            author = entry.get("author")

            return FetchResult(
                id=entry_id,
                source_id=source.id,
                title=title,
                content=content,
                url=url,
                published_at=published_at,
                fetched_at=fetched_at,
                author=author,
                metadata={
                    "tags": [t.get("term") for t in entry.get("tags", []) if t.get("term")]
                },
            )
        except Exception:
            return None

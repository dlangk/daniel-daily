import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import yaml


@dataclass
class ContentFile:
    id: str
    source_id: str
    source_name: str
    title: str
    url: str
    published_at: datetime
    fetched_at: datetime
    category: str
    author: Optional[str]
    content: str
    file_path: Path


class MarkdownStore:
    def __init__(self, content_dir: Path, briefs_dir: Path):
        self._content_dir = content_dir
        self._briefs_dir = briefs_dir
        self._content_dir.mkdir(parents=True, exist_ok=True)
        self._briefs_dir.mkdir(parents=True, exist_ok=True)

    def _slugify(self, text: str) -> str:
        slug = text.lower()
        slug = re.sub(r"[^\w\s-]", "", slug)
        slug = re.sub(r"[\s_]+", "-", slug)
        slug = re.sub(r"-+", "-", slug)
        return slug[:50].strip("-")

    def store_content(
        self,
        content_id: str,
        source_id: str,
        source_name: str,
        title: str,
        url: str,
        content: str,
        published_at: datetime,
        fetched_at: datetime,
        category: str,
        author: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> Path:
        source_dir = self._content_dir / source_id
        source_dir.mkdir(parents=True, exist_ok=True)

        date_str = published_at.strftime("%Y-%m-%d")
        slug = self._slugify(title)
        filename = f"{date_str}-{slug}.md"
        file_path = source_dir / filename

        front_matter = {
            "id": content_id,
            "source_id": source_id,
            "source_name": source_name,
            "title": title,
            "url": url,
            "published_at": published_at.isoformat(),
            "fetched_at": fetched_at.isoformat(),
            "category": category,
        }
        if author:
            front_matter["author"] = author
        if metadata:
            front_matter["metadata"] = metadata

        md_content = "---\n"
        md_content += yaml.dump(front_matter, default_flow_style=False, allow_unicode=True)
        md_content += "---\n\n"
        md_content += content

        with open(file_path, "w") as f:
            f.write(md_content)

        return file_path

    def get_content_since(self, since: datetime) -> list[ContentFile]:
        results = []
        for md_file in self._content_dir.rglob("*.md"):
            content_file = self._parse_content_file(md_file)
            if content_file and content_file.fetched_at >= since:
                results.append(content_file)
        results.sort(key=lambda x: x.published_at, reverse=True)
        return results

    def get_content_by_source(self, source_id: str) -> list[ContentFile]:
        source_dir = self._content_dir / source_id
        if not source_dir.exists():
            return []
        results = []
        for md_file in source_dir.glob("*.md"):
            content_file = self._parse_content_file(md_file)
            if content_file:
                results.append(content_file)
        results.sort(key=lambda x: x.published_at, reverse=True)
        return results

    def get_content_by_path(self, relative_path: str) -> Optional[ContentFile]:
        file_path = self._content_dir.parent / relative_path
        if not file_path.exists():
            return None
        return self._parse_content_file(file_path)

    def _parse_content_file(self, file_path: Path) -> Optional[ContentFile]:
        try:
            with open(file_path) as f:
                text = f.read()

            if not text.startswith("---"):
                return None

            end = text.find("---", 3)
            if end < 0:
                return None

            front_matter_str = text[3:end]
            content = text[end + 3:].strip()
            front_matter = yaml.safe_load(front_matter_str)

            return ContentFile(
                id=front_matter["id"],
                source_id=front_matter["source_id"],
                source_name=front_matter["source_name"],
                title=front_matter["title"],
                url=front_matter["url"],
                published_at=datetime.fromisoformat(front_matter["published_at"]),
                fetched_at=datetime.fromisoformat(front_matter["fetched_at"]),
                category=front_matter["category"],
                author=front_matter.get("author"),
                content=content,
                file_path=file_path,
            )
        except Exception:
            return None

    def store_brief(
        self,
        content: str,
        generated_at: datetime,
        window_from: datetime,
        window_to: datetime,
        sources_analyzed: int,
        model: str,
        source_map: dict[str, str],
    ) -> Path:
        date_str = generated_at.strftime("%Y-%m-%d")
        filename = f"{date_str}-brief.md"
        file_path = self._briefs_dir / filename

        front_matter = {
            "generated_at": generated_at.isoformat(),
            "content_window": {
                "from": window_from.isoformat(),
                "to": window_to.isoformat(),
            },
            "sources_analyzed": sources_analyzed,
            "model": model,
            "source_map": source_map,
        }

        md_content = "---\n"
        md_content += yaml.dump(front_matter, default_flow_style=False, allow_unicode=True)
        md_content += "---\n\n"
        md_content += content

        with open(file_path, "w") as f:
            f.write(md_content)

        return file_path

    def get_latest_brief(self) -> Optional[tuple[dict, str, Path]]:
        briefs = sorted(self._briefs_dir.glob("*-brief.md"), reverse=True)
        if not briefs:
            return None
        return self._parse_brief(briefs[0])

    def get_brief_by_date(self, date_str: str) -> Optional[tuple[dict, str, Path]]:
        file_path = self._briefs_dir / f"{date_str}-brief.md"
        if not file_path.exists():
            return None
        return self._parse_brief(file_path)

    def list_briefs(self) -> list[tuple[str, Path]]:
        briefs = sorted(self._briefs_dir.glob("*-brief.md"), reverse=True)
        results = []
        for brief_path in briefs:
            date_str = brief_path.stem.replace("-brief", "")
            results.append((date_str, brief_path))
        return results

    def _parse_brief(self, file_path: Path) -> Optional[tuple[dict, str, Path]]:
        try:
            with open(file_path) as f:
                text = f.read()

            if not text.startswith("---"):
                return None

            end = text.find("---", 3)
            if end < 0:
                return None

            front_matter_str = text[3:end]
            content = text[end + 3:].strip()
            front_matter = yaml.safe_load(front_matter_str)

            return (front_matter, content, file_path)
        except Exception:
            return None

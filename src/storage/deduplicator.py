import json
from pathlib import Path


class Deduplicator:
    def __init__(self, index_path: Path):
        self._index_path = index_path
        self._ids: set[str] = set()
        self._load()

    def _load(self) -> None:
        if self._index_path.exists():
            with open(self._index_path) as f:
                data = json.load(f)
                self._ids = set(data.get("ids", []))

    def _save(self) -> None:
        self._index_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._index_path, "w") as f:
            json.dump({"ids": list(self._ids)}, f)

    def exists(self, content_id: str) -> bool:
        return content_id in self._ids

    def add(self, content_id: str) -> None:
        self._ids.add(content_id)
        self._save()

    def rebuild_from_files(self, content_dir: Path) -> int:
        self._ids.clear()
        count = 0
        for md_file in content_dir.rglob("*.md"):
            with open(md_file) as f:
                content = f.read()
            if content.startswith("---"):
                end = content.find("---", 3)
                if end > 0:
                    front_matter = content[3:end]
                    for line in front_matter.split("\n"):
                        if line.startswith("id:"):
                            content_id = line[3:].strip().strip('"').strip("'")
                            self._ids.add(content_id)
                            count += 1
                            break
        self._save()
        return count

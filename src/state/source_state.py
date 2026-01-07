import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class FetchHistoryEntry:
    timestamp: str
    success: bool
    items_fetched: int = 0
    error: Optional[str] = None
    duration_seconds: float = 0.0


@dataclass
class SourceState:
    source_id: str
    last_fetch_attempt: Optional[str] = None
    last_successful_fetch: Optional[str] = None
    last_fetch_success: bool = False
    last_error: Optional[str] = None
    last_error_type: Optional[str] = None
    items_fetched_last_run: int = 0
    total_items_fetched: int = 0
    consecutive_failures: int = 0
    fetch_history: list[FetchHistoryEntry] = field(default_factory=list)


class SourceStateManager:
    MAX_HISTORY_ENTRIES = 10

    def __init__(self, state_dir: Path):
        self._state_dir = state_dir
        self._state_file = state_dir / "sources.json"
        self._states: dict[str, SourceState] = {}
        self._load()

    def _load(self) -> None:
        if not self._state_file.exists():
            return
        try:
            with open(self._state_file) as f:
                data = json.load(f)
            for source_id, state_data in data.items():
                history = [
                    FetchHistoryEntry(**h)
                    for h in state_data.pop("fetch_history", [])
                ]
                self._states[source_id] = SourceState(
                    **state_data, fetch_history=history
                )
        except Exception:
            pass

    def _save(self) -> None:
        self._state_dir.mkdir(parents=True, exist_ok=True)
        data = {}
        for source_id, state in self._states.items():
            state_dict = asdict(state)
            data[source_id] = state_dict
        with open(self._state_file, "w") as f:
            json.dump(data, f, indent=2)

    def get_state(self, source_id: str) -> Optional[SourceState]:
        return self._states.get(source_id)

    def get_all_states(self) -> dict[str, SourceState]:
        return dict(self._states)

    def record_success(
        self, source_id: str, items_fetched: int, duration: float
    ) -> None:
        now = datetime.utcnow().isoformat() + "Z"
        state = self._states.get(source_id) or SourceState(source_id=source_id)

        state.last_fetch_attempt = now
        state.last_successful_fetch = now
        state.last_fetch_success = True
        state.last_error = None
        state.last_error_type = None
        state.items_fetched_last_run = items_fetched
        state.total_items_fetched += items_fetched
        state.consecutive_failures = 0

        entry = FetchHistoryEntry(
            timestamp=now,
            success=True,
            items_fetched=items_fetched,
            duration_seconds=round(duration, 2),
        )
        state.fetch_history.insert(0, entry)
        state.fetch_history = state.fetch_history[: self.MAX_HISTORY_ENTRIES]

        self._states[source_id] = state
        self._save()

    def record_failure(
        self, source_id: str, error: Exception, duration: float
    ) -> None:
        now = datetime.utcnow().isoformat() + "Z"
        state = self._states.get(source_id) or SourceState(source_id=source_id)

        state.last_fetch_attempt = now
        state.last_fetch_success = False
        state.last_error = str(error)
        state.last_error_type = type(error).__name__
        state.items_fetched_last_run = 0
        state.consecutive_failures += 1

        entry = FetchHistoryEntry(
            timestamp=now,
            success=False,
            error=str(error),
            duration_seconds=round(duration, 2),
        )
        state.fetch_history.insert(0, entry)
        state.fetch_history = state.fetch_history[: self.MAX_HISTORY_ENTRIES]

        self._states[source_id] = state
        self._save()

    def get_sources_needing_attention(self) -> list[SourceState]:
        return [
            s for s in self._states.values()
            if s.consecutive_failures > 0 or not s.last_fetch_success
        ]

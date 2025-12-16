"""Conversation store for session archival.

Stores completed conversation sessions as JSONL records
for later retrieval and analysis.
"""

import json
from typing import List, Optional, Iterator
from pathlib import Path
from datetime import datetime

from . import SessionRecord


class ConversationStore:
    """Manages conversation session archives.

    Stores sessions as JSONL (one JSON record per line) for
    efficient append-only writes and line-by-line reading.
    """

    def __init__(self, archive_path: Path) -> None:
        """Initialize the conversation store.

        Args:
            archive_path: Path to the JSONL archive file
        """
        self._archive_path = archive_path
        self._archive_path.parent.mkdir(parents=True, exist_ok=True)

    def save_session(self, session: SessionRecord) -> None:
        """Save a session record to the archive.

        Args:
            session: The session record to save
        """
        # Ensure ended_at is set
        if session.ended_at is None:
            session.ended_at = datetime.now()

        # Append to JSONL file
        with open(self._archive_path, "a", encoding="utf-8") as f:
            json.dump(session.to_dict(), f)
            f.write("\n")

    def get_session(self, session_id: str) -> Optional[SessionRecord]:
        """Get a specific session by ID.

        Args:
            session_id: The session ID to find

        Returns:
            SessionRecord if found, None otherwise
        """
        for session in self._iter_sessions():
            if session.session_id == session_id:
                return session
        return None

    def get_recent_sessions(self, limit: int = 10) -> List[SessionRecord]:
        """Get the most recent sessions.

        Args:
            limit: Maximum number of sessions to return

        Returns:
            List of recent sessions, newest first
        """
        sessions = list(self._iter_sessions())
        # Sort by started_at descending
        sessions.sort(key=lambda s: s.started_at, reverse=True)
        return sessions[:limit]

    def search_sessions(
        self,
        model: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[SessionRecord]:
        """Search sessions by criteria.

        Args:
            model: Filter by model used
            start_date: Filter sessions starting after this date
            end_date: Filter sessions starting before this date

        Returns:
            List of matching sessions
        """
        results = []

        for session in self._iter_sessions():
            # Apply filters
            if model and model not in session.models_used:
                continue
            if start_date and session.started_at < start_date:
                continue
            if end_date and session.started_at > end_date:
                continue

            results.append(session)

        return results

    def get_statistics(self) -> dict:
        """Get aggregate statistics about stored sessions.

        Returns:
            Dictionary with session statistics
        """
        total_sessions = 0
        total_tokens = 0
        total_drift_events = 0
        models_used: dict = {}
        artifacts_generated: dict = {}

        for session in self._iter_sessions():
            total_sessions += 1
            total_tokens += session.token_count
            total_drift_events += session.drift_events

            for model in session.models_used:
                models_used[model] = models_used.get(model, 0) + 1

            for artifact in session.artifacts_generated:
                artifacts_generated[artifact] = (
                    artifacts_generated.get(artifact, 0) + 1
                )

        return {
            "total_sessions": total_sessions,
            "total_tokens": total_tokens,
            "total_drift_events": total_drift_events,
            "models_used": models_used,
            "artifacts_generated": artifacts_generated,
        }

    def delete_session(self, session_id: str) -> bool:
        """Delete a session from the archive.

        Note: This rewrites the entire file, which is expensive.
        Use sparingly.

        Args:
            session_id: The session ID to delete

        Returns:
            True if deleted, False if not found
        """
        sessions = [
            s for s in self._iter_sessions()
            if s.session_id != session_id
        ]

        if len(sessions) == len(list(self._iter_sessions())):
            return False

        # Rewrite file without deleted session
        self._rewrite_sessions(sessions)
        return True

    def clear(self) -> None:
        """Clear all session records."""
        if self._archive_path.exists():
            self._archive_path.unlink()

    def _iter_sessions(self) -> Iterator[SessionRecord]:
        """Iterate over all stored sessions.

        Yields:
            SessionRecord objects
        """
        if not self._archive_path.exists():
            return

        with open(self._archive_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                try:
                    data = json.loads(line)
                    yield self._dict_to_session(data)
                except json.JSONDecodeError:
                    continue

    def _dict_to_session(self, data: dict) -> SessionRecord:
        """Convert dictionary to SessionRecord.

        Args:
            data: Dictionary from JSON

        Returns:
            SessionRecord instance
        """
        return SessionRecord(
            session_id=data["session_id"],
            started_at=datetime.fromisoformat(data["started_at"]),
            ended_at=(
                datetime.fromisoformat(data["ended_at"])
                if data.get("ended_at")
                else None
            ),
            models_used=data.get("models_used", []),
            summary_xml=data.get("summary_xml", ""),
            token_count=data.get("token_count", 0),
            drift_events=data.get("drift_events", 0),
            waypoints=data.get("waypoints", []),
            artifacts_generated=data.get("artifacts_generated", []),
        )

    def _rewrite_sessions(self, sessions: List[SessionRecord]) -> None:
        """Rewrite the archive file with given sessions.

        Args:
            sessions: Sessions to write
        """
        with open(self._archive_path, "w", encoding="utf-8") as f:
            for session in sessions:
                json.dump(session.to_dict(), f)
                f.write("\n")

"""Conversation store for session archival.

Stores completed conversation sessions as JSONL records
for later retrieval and analysis.

Uses atomic writes and file locking for data integrity.
"""

import json
import os
import sys
import tempfile
import shutil
from typing import List, Optional, Iterator
from pathlib import Path
from datetime import datetime
from contextlib import contextmanager

from . import SessionRecord


class ConversationStore:
    """Manages conversation session archives.

    Stores sessions as JSONL (one JSON record per line) for
    efficient append-only writes and line-by-line reading.

    Uses atomic writes (temp file + rename) and file locking
    to prevent data corruption from concurrent access.
    """

    def __init__(self, archive_path: Path) -> None:
        """Initialize the conversation store.

        Args:
            archive_path: Path to the JSONL archive file
        """
        self._archive_path = archive_path
        self._archive_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock_path = archive_path.with_suffix('.lock')

    @contextmanager
    def _file_lock(self):
        """Cross-platform file locking context manager."""
        lock_file = None
        try:
            # Create/open lock file
            lock_file = open(self._lock_path, 'w')

            # Platform-specific locking
            if sys.platform == 'win32':
                import msvcrt
                msvcrt.locking(lock_file.fileno(), msvcrt.LK_LOCK, 1)
            else:
                import fcntl
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)

            yield

        finally:
            if lock_file:
                # Unlock
                if sys.platform == 'win32':
                    import msvcrt
                    try:
                        msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
                    except OSError:
                        pass  # Already unlocked
                else:
                    import fcntl
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

                lock_file.close()

                # Clean up lock file
                try:
                    self._lock_path.unlink()
                except OSError:
                    pass  # May be held by another process

    def _atomic_write(self, sessions: List[SessionRecord]) -> None:
        """Atomically write sessions to archive file.

        Uses write-to-temp-then-rename pattern for crash safety.

        Args:
            sessions: Sessions to write
        """
        # Create temp file in same directory (for atomic rename)
        temp_fd, temp_path = tempfile.mkstemp(
            dir=self._archive_path.parent,
            suffix='.tmp'
        )

        try:
            # Write to temp file
            with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
                for session in sessions:
                    json.dump(session.to_dict(), f)
                    f.write('\n')
                f.flush()
                os.fsync(f.fileno())  # Ensure data is on disk

            # Atomic rename (overwrites existing file)
            shutil.move(temp_path, str(self._archive_path))

        except Exception:
            # Clean up temp file on failure
            try:
                os.unlink(temp_path)
            except OSError:
                pass
            raise

    def save_session(self, session: SessionRecord) -> None:
        """Save a session record to the archive.

        Uses atomic write with file locking for thread safety.

        Args:
            session: The session record to save
        """
        # Ensure ended_at is set
        if session.ended_at is None:
            session.ended_at = datetime.now()

        with self._file_lock():
            # Load existing sessions
            existing = list(self._iter_sessions_unlocked())

            # Update or append
            found = False
            for i, s in enumerate(existing):
                if s.session_id == session.session_id:
                    existing[i] = session
                    found = True
                    break

            if not found:
                existing.append(session)

            # Atomic write
            self._atomic_write(existing)

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

    def get_recent_sessions(
        self,
        limit: int = 10,
        offset: int = 0
    ) -> List[SessionRecord]:
        """Get the most recent sessions with pagination.

        Args:
            limit: Maximum number of sessions to return
            offset: Number of sessions to skip

        Returns:
            List of recent sessions, newest first
        """
        sessions = list(self._iter_sessions())
        # Sort by started_at descending
        sessions.sort(key=lambda s: s.started_at, reverse=True)
        return sessions[offset:offset + limit]

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

        Uses atomic write for crash safety.

        Args:
            session_id: The session ID to delete

        Returns:
            True if deleted, False if not found
        """
        with self._file_lock():
            sessions = list(self._iter_sessions_unlocked())
            original_count = len(sessions)

            sessions = [s for s in sessions if s.session_id != session_id]

            if len(sessions) == original_count:
                return False

            # Atomic write
            self._atomic_write(sessions)
            return True

    def clear(self) -> None:
        """Clear all session records."""
        with self._file_lock():
            if self._archive_path.exists():
                self._archive_path.unlink()

    def _iter_sessions(self) -> Iterator[SessionRecord]:
        """Iterate over all stored sessions (with locking).

        Yields:
            SessionRecord objects
        """
        with self._file_lock():
            yield from self._iter_sessions_unlocked()

    def _iter_sessions_unlocked(self) -> Iterator[SessionRecord]:
        """Iterate over sessions without acquiring lock.

        Use only when lock is already held.

        Yields:
            SessionRecord objects
        """
        if not self._archive_path.exists():
            return

        with open(self._archive_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue

                try:
                    data = json.loads(line)
                    yield self._dict_to_session(data)
                except json.JSONDecodeError as e:
                    # Log but don't crash on malformed lines
                    print(f"Warning: Skipping malformed line {line_num}: {e}")
                    continue
                except KeyError as e:
                    print(f"Warning: Missing field in line {line_num}: {e}")
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
            messages=data.get("messages", []),
            fork_source_session_id=data.get("fork_source_session_id"),
            fork_point_index=data.get("fork_point_index"),
        )

    def get_forks_of_session(self, session_id: str) -> List[SessionRecord]:
        """Get all sessions that were forked from a given session.

        Args:
            session_id: The source session ID

        Returns:
            List of forked sessions
        """
        return [
            s for s in self._iter_sessions()
            if s.fork_source_session_id == session_id
        ]

    def validate_fork_references(self) -> List[str]:
        """Validate all fork references point to existing sessions.

        Returns:
            List of session IDs with invalid fork references
        """
        all_ids = {s.session_id for s in self._iter_sessions()}
        invalid = []

        for session in self._iter_sessions():
            if session.fork_source_session_id:
                if session.fork_source_session_id not in all_ids:
                    invalid.append(session.session_id)

        return invalid

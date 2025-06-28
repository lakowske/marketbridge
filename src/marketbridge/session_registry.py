"""
MarketBridge Session Registry

Persistent registry for tracking active browser sessions inspired by browser-bunny's
session management. Provides a centralized way to manage session state across
server restarts and multiple client connections.
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class SessionRegistry:
    """
    Persistent registry for browser sessions with automatic cleanup and health monitoring.

    Similar to browser-bunny's session manager but integrated with MarketBridge's
    existing SessionManager and BrowserManager classes.
    """

    def __init__(self, registry_file: Optional[str] = None):
        """
        Initialize the session registry.

        Args:
            registry_file: Path to the registry file. Defaults to
                          ~/.marketbridge/browser_sessions_registry.json
        """
        if registry_file is None:
            registry_dir = Path.home() / ".marketbridge"
            registry_dir.mkdir(parents=True, exist_ok=True)
            self.registry_file = registry_dir / "browser_sessions_registry.json"
        else:
            self.registry_file = Path(registry_file)

        # In-memory session storage
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.active_sessions: Set[str] = set()

        # Load existing registry
        self._load_registry()

        logger.info(
            f"Session registry initialized - registry_file: {self.registry_file}, "
            f"loaded_sessions: {len(self.sessions)}"
        )

    def _load_registry(self) -> None:
        """Load the session registry from disk."""
        if not self.registry_file.exists():
            logger.debug("Registry file does not exist, starting with empty registry")
            return

        try:
            with open(self.registry_file, "r") as f:
                data = json.load(f)
                self.sessions = data.get("sessions", {})
                self.active_sessions = set(data.get("active_sessions", []))

            logger.info(f"Loaded {len(self.sessions)} sessions from registry")

            # Validate loaded sessions
            self._validate_loaded_sessions()

        except (json.JSONDecodeError, FileNotFoundError) as e:
            logger.warning(f"Failed to load session registry: {e}, starting fresh")
            self.sessions = {}
            self.active_sessions = set()

    def _save_registry(self) -> None:
        """Save the session registry to disk."""
        try:
            # Ensure directory exists
            self.registry_file.parent.mkdir(parents=True, exist_ok=True)

            data = {
                "sessions": self.sessions,
                "active_sessions": list(self.active_sessions),
                "last_updated": datetime.now().isoformat(),
            }

            # Write to temporary file first, then rename for atomicity
            temp_file = self.registry_file.with_suffix(".tmp")
            with open(temp_file, "w") as f:
                json.dump(data, f, indent=2)

            temp_file.rename(self.registry_file)

            logger.debug(f"Session registry saved - sessions: {len(self.sessions)}")

        except Exception as e:
            logger.error(f"Failed to save session registry: {e}")

    def _validate_loaded_sessions(self) -> None:
        """Validate loaded sessions and remove invalid ones."""
        invalid_sessions = []

        for session_id, session_data in self.sessions.items():
            # Check if session data is complete
            required_fields = [
                "session_id",
                "session_name",
                "created_at",
                "last_activity",
            ]
            if not all(field in session_data for field in required_fields):
                invalid_sessions.append(session_id)
                continue

            # Check if session is too old (older than 7 days)
            try:
                last_activity = datetime.fromisoformat(session_data["last_activity"])
                age_days = (datetime.now() - last_activity).days
                if age_days > 7:
                    invalid_sessions.append(session_id)
                    logger.info(
                        f"Removing old session: {session_id} (age: {age_days} days)"
                    )
                    continue
            except ValueError:
                invalid_sessions.append(session_id)
                continue

        # Remove invalid sessions
        for session_id in invalid_sessions:
            self.sessions.pop(session_id, None)
            self.active_sessions.discard(session_id)

        if invalid_sessions:
            logger.info(
                f"Removed {len(invalid_sessions)} invalid sessions during validation"
            )
            self._save_registry()

    def create_session(
        self,
        session_name: str,
        page_url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Create a new browser session entry.

        Args:
            session_name: Human-readable session name
            page_url: Optional initial page URL
            metadata: Additional session metadata

        Returns:
            Session ID (UUID)

        Raises:
            ValueError: If session name already exists
        """
        # Check if session name already exists
        for session_data in self.sessions.values():
            if session_data.get("session_name") == session_name:
                raise ValueError(f"Session name '{session_name}' already exists")

        session_id = str(uuid.uuid4())
        now = datetime.now().isoformat()

        session_data = {
            "session_id": session_id,
            "session_name": session_name,
            "created_at": now,
            "last_activity": now,
            "current_url": page_url,
            "active": True,
            "page_count": 0,
            "browser_type": "chromium",
            "metadata": metadata or {},
        }

        self.sessions[session_id] = session_data
        self.active_sessions.add(session_id)
        self._save_registry()

        logger.info(
            f"Created new session - session_id: {session_id}, "
            f"session_name: {session_name}, url: {page_url}"
        )

        return session_id

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session data by ID.

        Args:
            session_id: Session ID to retrieve

        Returns:
            Session data dictionary or None if not found
        """
        session_data = self.sessions.get(session_id)
        if session_data:
            # Update last activity
            session_data["last_activity"] = datetime.now().isoformat()
            self._save_registry()

        return session_data

    def get_session_by_name(self, session_name: str) -> Optional[Dict[str, Any]]:
        """
        Get session data by name.

        Args:
            session_name: Session name to retrieve

        Returns:
            Session data dictionary or None if not found
        """
        for session_data in self.sessions.values():
            if session_data.get("session_name") == session_name:
                # Update last activity
                session_data["last_activity"] = datetime.now().isoformat()
                self._save_registry()
                return session_data

        return None

    def update_session(
        self,
        session_id: str,
        url: Optional[str] = None,
        page_count: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
        active: Optional[bool] = None,
    ) -> bool:
        """
        Update session data.

        Args:
            session_id: Session ID to update
            url: New current URL
            page_count: Updated page count
            metadata: Additional metadata to merge
            active: Whether session is active

        Returns:
            True if session was updated, False if not found
        """
        if session_id not in self.sessions:
            return False

        session_data = self.sessions[session_id]
        session_data["last_activity"] = datetime.now().isoformat()

        if url is not None:
            session_data["current_url"] = url

        if page_count is not None:
            session_data["page_count"] = page_count

        if metadata is not None:
            session_data["metadata"].update(metadata)

        if active is not None:
            session_data["active"] = active
            if active:
                self.active_sessions.add(session_id)
            else:
                self.active_sessions.discard(session_id)

        self._save_registry()

        logger.debug(
            f"Updated session - session_id: {session_id}, url: {url}, "
            f"page_count: {page_count}, active: {active}"
        )

        return True

    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session from the registry.

        Args:
            session_id: Session ID to delete

        Returns:
            True if session was deleted, False if not found
        """
        if session_id not in self.sessions:
            return False

        session_data = self.sessions.pop(session_id)
        self.active_sessions.discard(session_id)
        self._save_registry()

        logger.info(
            f"Deleted session - session_id: {session_id}, "
            f"session_name: {session_data.get('session_name')}"
        )

        return True

    def list_sessions(self, active_only: bool = False) -> List[Dict[str, Any]]:
        """
        List all sessions or only active ones.

        Args:
            active_only: If True, only return active sessions

        Returns:
            List of session data dictionaries
        """
        sessions = list(self.sessions.values())

        if active_only:
            sessions = [s for s in sessions if s.get("active", False)]

        # Sort by last activity (most recent first)
        sessions.sort(key=lambda s: s.get("last_activity", ""), reverse=True)

        return sessions

    def session_exists(self, session_id: str) -> bool:
        """
        Check if a session exists.

        Args:
            session_id: Session ID to check

        Returns:
            True if session exists, False otherwise
        """
        return session_id in self.sessions

    def session_name_exists(self, session_name: str) -> bool:
        """
        Check if a session name exists.

        Args:
            session_name: Session name to check

        Returns:
            True if session name exists, False otherwise
        """
        for session_data in self.sessions.values():
            if session_data.get("session_name") == session_name:
                return True
        return False

    def get_active_sessions(self) -> List[Dict[str, Any]]:
        """
        Get all active sessions.

        Returns:
            List of active session data dictionaries
        """
        return self.list_sessions(active_only=True)

    def cleanup_inactive_sessions(self, max_age_hours: int = 24) -> List[str]:
        """
        Clean up inactive sessions older than specified age.

        Args:
            max_age_hours: Maximum age in hours before sessions are cleaned up

        Returns:
            List of deleted session IDs
        """
        from datetime import timedelta

        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        deleted_sessions = []

        for session_id, session_data in list(self.sessions.items()):
            try:
                last_activity = datetime.fromisoformat(session_data["last_activity"])
                if last_activity < cutoff_time and not session_data.get(
                    "active", False
                ):
                    self.delete_session(session_id)
                    deleted_sessions.append(session_id)
            except (ValueError, KeyError) as e:
                logger.warning(f"Failed to parse session data for {session_id}: {e}")
                # Delete malformed session data
                self.delete_session(session_id)
                deleted_sessions.append(session_id)

        if deleted_sessions:
            logger.info(
                f"Cleaned up {len(deleted_sessions)} inactive sessions: {deleted_sessions}"
            )

        return deleted_sessions

    async def health_check_session(self, session_id: str) -> bool:
        """
        Perform a health check on a session.

        Args:
            session_id: Session ID to check

        Returns:
            True if session is healthy, False otherwise
        """
        # This is a placeholder - in a real implementation, this would
        # ping the actual browser session to verify it's responsive
        session_data = self.get_session(session_id)
        if not session_data:
            return False

        # For now, just check if the session is marked as active
        # and was accessed recently (within last hour)
        try:
            last_activity = datetime.fromisoformat(session_data["last_activity"])
            age_minutes = (datetime.now() - last_activity).total_seconds() / 60
            is_healthy = session_data.get("active", False) and age_minutes < 60

            logger.debug(
                f"Health check - session_id: {session_id}, healthy: {is_healthy}, "
                f"age_minutes: {age_minutes:.1f}"
            )

            return is_healthy

        except ValueError:
            return False

    def get_registry_stats(self) -> Dict[str, Any]:
        """
        Get registry statistics.

        Returns:
            Dictionary with registry statistics
        """
        total_sessions = len(self.sessions)
        active_sessions = len(self.active_sessions)

        # Calculate age distribution
        age_distribution = {"<1h": 0, "1-24h": 0, "1-7d": 0, ">7d": 0}
        now = datetime.now()

        for session_data in self.sessions.values():
            try:
                last_activity = datetime.fromisoformat(session_data["last_activity"])
                age_hours = (now - last_activity).total_seconds() / 3600

                if age_hours < 1:
                    age_distribution["<1h"] += 1
                elif age_hours < 24:
                    age_distribution["1-24h"] += 1
                elif age_hours < 168:  # 7 days
                    age_distribution["1-7d"] += 1
                else:
                    age_distribution[">7d"] += 1
            except ValueError:
                age_distribution[">7d"] += 1

        return {
            "total_sessions": total_sessions,
            "active_sessions": active_sessions,
            "inactive_sessions": total_sessions - active_sessions,
            "age_distribution": age_distribution,
            "registry_file": str(self.registry_file),
        }

    def __len__(self) -> int:
        """Return the number of sessions in the registry."""
        return len(self.sessions)

    def __contains__(self, session_id: str) -> bool:
        """Check if a session ID is in the registry."""
        return session_id in self.sessions

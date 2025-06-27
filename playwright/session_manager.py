"""
Playwright Session Manager

Manages persistent browser sessions that can be saved to disk and restored
across multiple script runs. Sessions include browser state, cookies,
local storage, and other context data.
"""

import json
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages persistent Playwright browser sessions."""

    def __init__(self, sessions_dir: Optional[str] = None):
        """
        Initialize session manager.

        Args:
            sessions_dir: Directory to store session data.
                         Defaults to ~/.marketbridge/playwright_sessions/
        """
        if sessions_dir is None:
            self.sessions_dir = Path.home() / ".marketbridge" / "playwright_sessions"
        else:
            self.sessions_dir = Path(sessions_dir)

        # Ensure sessions directory exists
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Session manager initialized - sessions_dir: {self.sessions_dir}")

    def create_session(self, name: str, description: str = "") -> Dict[str, Any]:
        """
        Create a new session entry.

        Args:
            name: Unique session name
            description: Optional description of the session

        Returns:
            Session metadata dictionary

        Raises:
            ValueError: If session already exists
        """
        if self.session_exists(name):
            raise ValueError(f"Session '{name}' already exists")

        session_dir = self.sessions_dir / name
        session_dir.mkdir(exist_ok=True)

        metadata = {
            "name": name,
            "description": description,
            "created_at": datetime.now().isoformat(),
            "last_used": datetime.now().isoformat(),
            "session_dir": str(session_dir),
            "browser_context_dir": str(session_dir / "browser_context"),
            "metadata_file": str(session_dir / "metadata.json"),
        }

        # Save metadata
        with open(session_dir / "metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)

        logger.info(f"Created new session: {name}")
        return metadata

    def load_session(self, name: str) -> Dict[str, Any]:
        """
        Load session metadata from disk.

        Args:
            name: Session name to load

        Returns:
            Session metadata dictionary

        Raises:
            ValueError: If session doesn't exist
        """
        if not self.session_exists(name):
            raise ValueError(f"Session '{name}' does not exist")

        session_dir = self.sessions_dir / name
        metadata_file = session_dir / "metadata.json"

        try:
            with open(metadata_file, "r") as f:
                metadata = json.load(f)

            # Update last used timestamp
            metadata["last_used"] = datetime.now().isoformat()

            # Save updated metadata
            with open(metadata_file, "w") as f:
                json.dump(metadata, f, indent=2)

            logger.info(f"Loaded session: {name}")
            return metadata  # type: ignore[no-any-return]

        except (json.JSONDecodeError, FileNotFoundError) as e:
            raise ValueError(f"Failed to load session '{name}': {e}") from e

    def save_session_state(self, name: str, state_data: Dict[str, Any]) -> None:
        """
        Save additional session state data.

        Args:
            name: Session name
            state_data: Additional state data to save
        """
        if not self.session_exists(name):
            raise ValueError(f"Session '{name}' does not exist")

        session_dir = self.sessions_dir / name
        state_file = session_dir / "state.json"

        with open(state_file, "w") as f:
            json.dump(state_data, f, indent=2)

        logger.debug(f"Saved state data for session: {name}")

    def load_session_state(self, name: str) -> Dict[str, Any]:
        """
        Load additional session state data.

        Args:
            name: Session name

        Returns:
            Session state data or empty dict if none exists
        """
        if not self.session_exists(name):
            raise ValueError(f"Session '{name}' does not exist")

        session_dir = self.sessions_dir / name
        state_file = session_dir / "state.json"

        try:
            with open(state_file, "r") as f:
                data: Dict[str, Any] = json.load(f)
                return data
        except (json.JSONDecodeError, FileNotFoundError):
            return {}

    def delete_session(self, name: str) -> None:
        """
        Delete a session and all its data.

        Args:
            name: Session name to delete

        Raises:
            ValueError: If session doesn't exist
        """
        if not self.session_exists(name):
            raise ValueError(f"Session '{name}' does not exist")

        session_dir = self.sessions_dir / name
        shutil.rmtree(session_dir)

        logger.info(f"Deleted session: {name}")

    def list_sessions(self) -> List[Dict[str, Any]]:
        """
        List all available sessions.

        Returns:
            List of session metadata dictionaries
        """
        sessions = []

        for session_dir in self.sessions_dir.iterdir():
            if session_dir.is_dir():
                metadata_file = session_dir / "metadata.json"
                if metadata_file.exists():
                    try:
                        with open(metadata_file, "r") as f:
                            metadata = json.load(f)
                        sessions.append(metadata)
                    except (json.JSONDecodeError, FileNotFoundError) as e:
                        logger.warning(
                            f"Failed to load session metadata from {metadata_file}: {e}"
                        )

        # Sort by last used (most recent first)
        sessions.sort(key=lambda s: s.get("last_used", ""), reverse=True)

        return sessions

    def session_exists(self, name: str) -> bool:
        """
        Check if a session exists.

        Args:
            name: Session name to check

        Returns:
            True if session exists, False otherwise
        """
        session_dir = self.sessions_dir / name
        metadata_file = session_dir / "metadata.json"
        return session_dir.exists() and metadata_file.exists()

    def get_browser_context_dir(self, name: str) -> str:
        """
        Get the browser context directory path for a session.

        Args:
            name: Session name

        Returns:
            Path to browser context directory

        Raises:
            ValueError: If session doesn't exist
        """
        if not self.session_exists(name):
            raise ValueError(f"Session '{name}' does not exist")

        return str(self.sessions_dir / name / "browser_context")

    def cleanup_old_sessions(self, max_age_days: int = 30) -> List[str]:
        """
        Clean up sessions older than specified age.

        Args:
            max_age_days: Maximum age in days before sessions are cleaned up

        Returns:
            List of deleted session names
        """
        from datetime import timedelta

        cutoff_date = datetime.now() - timedelta(days=max_age_days)
        deleted_sessions = []

        for session in self.list_sessions():
            try:
                last_used = datetime.fromisoformat(session["last_used"])
                if last_used < cutoff_date:
                    self.delete_session(session["name"])
                    deleted_sessions.append(session["name"])
            except (ValueError, KeyError) as e:
                logger.warning(
                    f"Failed to parse last_used for session {session.get('name')}: {e}"
                )

        if deleted_sessions:
            logger.info(
                f"Cleaned up {len(deleted_sessions)} old sessions: {deleted_sessions}"
            )

        return deleted_sessions

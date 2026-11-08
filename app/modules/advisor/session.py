"""
Session Management and Context Persistence for AI Advisor.
Thread-safe session storage tracking cumulative profile, conversation history,
active bundle state, and session ownership.
"""

import time
import threading
from typing import Dict, Any, List, Optional
from app.modules.advisor.profile import merge_profiles

class AdvisorSession:
    def __init__(self, session_id: str, owner_id: Optional[str] = None):
        self.session_id: str = session_id
        self.owner_id: Optional[str] = owner_id
        self.profile: Dict[str, Any] = {}
        self.history: List[Dict[str, str]] = []
        self.active_bundle: Optional[Dict[str, int]] = None
        self.downsell_level: int = 0
        self.created_at: float = time.time()
        self.updated_at: float = time.time()

    def update_profile(self, updates: Dict[str, Any]):
        self.profile = merge_profiles(self.profile, updates)
        self.updated_at = time.time()

    def append_turn(self, role: str, text: str):
        self.history.append({"role": role, "text": text})
        self.updated_at = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "owner_id": self.owner_id,
            "profile": self.profile,
            "history": self.history,
            "active_bundle": self.active_bundle,
            "downsell_level": self.downsell_level,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

class SessionStore:
    """Thread-safe in-memory session manager with ownership validation."""
    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        self._sessions: Dict[str, AdvisorSession] = {}
        self._mutex = threading.Lock()

    @classmethod
    def get_instance(cls) -> "SessionStore":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def get_or_create(self, session_id: str, owner_id: Optional[str] = None) -> AdvisorSession:
        with self._mutex:
            if session_id not in self._sessions:
                self._sessions[session_id] = AdvisorSession(session_id, owner_id)
            session = self._sessions[session_id]
            # Link owner_id if not yet set
            if owner_id and not session.owner_id:
                session.owner_id = owner_id
            return session

    def get(self, session_id: str) -> Optional[AdvisorSession]:
        with self._mutex:
            return self._sessions.get(session_id)

    def verify_ownership(self, session_id: str, user_id: str) -> bool:
        """Verifies if the session belongs to the requesting user."""
        with self._mutex:
            session = self._sessions.get(session_id)
            if not session or not session.owner_id:
                return True  # Public / unauthenticated session
            return session.owner_id == user_id

    def reset(self, session_id: str):
        with self._mutex:
            if session_id in self._sessions:
                del self._sessions[session_id]


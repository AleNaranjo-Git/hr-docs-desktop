from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Any, Dict


@dataclass
class SessionState:
    user_id: str
    email: str
    access_token: str
    refresh_token: str

    @staticmethod
    def from_supabase(session: Any) -> "SessionState":
        
        user = session.user
        email = getattr(user, "email", "") or ""
        user_id = getattr(user, "id", "") or ""
        return SessionState(
            user_id=user_id,
            email=email,
            access_token=session.access_token,
            refresh_token=session.refresh_token,
        )


class AppSession:
    current: Optional[SessionState] = None

    @classmethod
    def is_logged_in(cls) -> bool:
        return cls.current is not None

    @classmethod
    def clear(cls) -> None:
        cls.current = None
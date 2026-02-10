from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class SessionState:
    user_id: str
    email: str
    access_token: str
    refresh_token: str
    firm_id: str  # required tenant scope

    @staticmethod
    def from_supabase(session: Any) -> "SessionState":
        user = getattr(session, "user", None)
        email = getattr(user, "email", "") or ""
        user_id = getattr(user, "id", "") or ""

        return SessionState(
            user_id=user_id,
            email=email,
            access_token=getattr(session, "access_token", "") or "",
            refresh_token=getattr(session, "refresh_token", "") or "",
            firm_id="",
        )


class AppSession:
    current: Optional[SessionState] = None

    @classmethod
    def is_logged_in(cls) -> bool:
        return cls.current is not None

    @classmethod
    def clear(cls) -> None:
        cls.current = None

    @classmethod
    def require(cls) -> SessionState:
        if cls.current is None:
            raise RuntimeError("Not logged in.")
        return cls.current
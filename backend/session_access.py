"""Who may read or play a session.

- Sessions created while logged in belong to that user (``owner_user_id``).
- Guest sessions get a random secret token, returned once at creation; the
  browser sends it back as ``X-Session-Token``. Only its SHA-256 is stored.
- Admins may access every session.

Anything else gets the same 404 as a missing session, so session IDs can't be
probed for existence.
"""

import hashlib
import hmac
import secrets

from fastapi import Depends, Header, HTTPException, Request

from auth import get_current_user
from models.game_state import GameSession


def new_guest_token() -> str:
    return secrets.token_urlsafe(32)


def hash_guest_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def can_access(session: GameSession, user: dict | None, guest_token: str | None) -> bool:
    if user and user.get("role") == "admin":
        return True
    if session.owner_user_id:
        return bool(user) and user.get("id") == session.owner_user_id
    if session.guest_token_hash and guest_token:
        return hmac.compare_digest(hash_guest_token(guest_token), session.guest_token_hash)
    return False


async def get_authorized_session(
    session_id: str,
    request: Request,
    user: dict | None = Depends(get_current_user),
    x_session_token: str | None = Header(None, alias="X-Session-Token"),
) -> GameSession:
    """FastAPI dependency: load the session in the path if the caller may access it."""
    state = request.app.state
    session = state.state_manager.get_session(session_id)
    if session is None:
        session = await state.db.load_session(session_id)
        if session is not None:
            state.state_manager._sessions[session_id] = session
    if session is None or not can_access(session, user, x_session_token):
        raise HTTPException(status_code=404, detail="Session not found")
    return session

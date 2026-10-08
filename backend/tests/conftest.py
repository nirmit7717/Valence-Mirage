"""Shared pytest fixtures — offline app harness with fake LLM services.

The real FastAPI lifespan connects to ChromaDB, NVIDIA embeddings and LLM
clients. Tests swap it for a lifespan that wires real game engines, a temporary
SQLite database, and deterministic fakes for every network-backed component.
"""

from contextlib import asynccontextmanager

import pytest
from fastapi.testclient import TestClient
from passlib.context import CryptContext

import auth
import database
import main
from database import Database
from engines.combat_engine import CombatEngine
from engines.dice import DiceEngine
from engines.engagement_tracker import EngagementTracker
from engines.probability import ProbabilityEngine
from engines.state_manager import StateManager
from helpers import (
    FakeEnemyDesigner,
    FakeIntentParser,
    FakeNarrator,
    FakeNPCEngine,
    FakeRuleRetriever,
    make_planner,
)


@asynccontextmanager
async def _test_lifespan(app):
    app.state.intent_parser = FakeIntentParser()
    app.state.probability = ProbabilityEngine()
    app.state.dice = DiceEngine()
    app.state.narrator = FakeNarrator()
    app.state.state_manager = StateManager()
    app.state.campaign_planner = make_planner()
    app.state.npc_engine = FakeNPCEngine()
    app.state.combat_engine = CombatEngine()
    app.state.engagement_tracker = EngagementTracker()
    app.state.enemy_designer = FakeEnemyDesigner()
    app.state.vector_store = None
    app.state.rule_retriever = FakeRuleRetriever()

    db = Database()
    await db.connect()
    app.state.db = db
    app.state.session_locks = {}
    await main._ensure_admin(db)
    await main._assign_legacy_owners(db)
    try:
        yield
    finally:
        await db.close()


@pytest.fixture(autouse=True)
def fast_password_hashing(monkeypatch):
    """bcrypt at default cost makes every test slow; use the minimum cost."""
    monkeypatch.setattr(auth, "pwd_context", CryptContext(schemes=["bcrypt"], bcrypt__rounds=4))


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setattr(main.app.router, "lifespan_context", _test_lifespan)
    with TestClient(main.app) as test_client:
        yield test_client


@pytest.fixture
def app_state(client):
    return main.app.state


@pytest.fixture
def fixed_roll(monkeypatch):
    """Force every d20 roll in the action path to a given value."""

    def _set(value: int):
        monkeypatch.setattr(DiceEngine, "roll_d20", staticmethod(lambda: value))

    return _set


@pytest.fixture
def make_user(client):
    """Create a user in the test DB and return (user_dict, auth_headers)."""

    def _make(username: str = "player1", role: str = "player"):
        db = main.app.state.db
        user = client.portal.call(db.create_user, username, auth.hash_password("password123"), role)
        token = auth.create_access_token({"sub": user["id"], "username": username, "role": role})
        return user, {"Authorization": f"Bearer {token}"}

    return _make


@pytest.fixture
def admin_headers(client):
    db = main.app.state.db
    admin = client.portal.call(db.get_user_by_username, "admin")
    token = auth.create_access_token({"sub": admin["id"], "username": "admin", "role": "admin"})
    return {"Authorization": f"Bearer {token}"}

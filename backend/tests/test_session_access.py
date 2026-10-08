"""Bug 3: session routes must enforce ownership (owner, guest token, or admin)."""

import asyncio
import json

import pytest

import database
from database import Database
from helpers import act, create_session, get_session, make_intent, new_session
from models.game_state import GameSession

PROTECTED = [
    ("get", "/session/{sid}", None),
    ("get", "/session/{sid}/hydrate", None),
    ("get", "/session/{sid}/history", None),
    ("get", "/session/{sid}/npcs", None),
    ("get", "/session/{sid}/combat", None),
    ("post", "/session/{sid}/action", {"action": "I look around"}),
    ("post", "/session/{sid}/combat/resolve", {
        "combat_id": "x", "result": "victory", "player_hp": 10, "player_mana": 10,
        "enemy_name": "Goblin Scavenger", "turns_taken": 3,
    }),
    ("delete", "/session/{sid}", None),
]


def _call(client, method, path, body, headers):
    kwargs = {"headers": headers}
    if body is not None:
        kwargs["json"] = body
    return getattr(client, method)(path, **kwargs)


# ─── Guests ───


def test_guest_session_returns_a_token_once(client):
    data, headers = new_session(client)
    assert data["guest_token"]
    assert headers["X-Session-Token"] == data["guest_token"]
    stored = get_session(data["session_id"])
    assert stored.guest_token_hash and stored.guest_token_hash != data["guest_token"]
    assert stored.owner_user_id is None


def test_guest_token_grants_access(client):
    session_id, headers = create_session(client)
    assert client.get(f"/session/{session_id}/hydrate", headers=headers).status_code == 200


@pytest.mark.parametrize(
    "headers",
    [{}, {"X-Session-Token": "wrong-token"}, {"X-Session-Token": ""}],
    ids=["no-token", "wrong-token", "empty-token"],
)
def test_guest_session_rejects_other_callers(client, headers):
    session_id, _ = create_session(client)
    assert client.get(f"/session/{session_id}/hydrate", headers=headers).status_code == 404


def test_one_guest_cannot_use_another_guests_session(client):
    first_id, _ = create_session(client)
    _, second_headers = create_session(client)
    assert client.get(f"/session/{first_id}", headers=second_headers).status_code == 404


# ─── Logged-in owners ───


def test_logged_in_session_is_owned_and_has_no_guest_token(client, make_user):
    user, headers = make_user("owner1")
    data, _ = new_session(client, headers=headers)
    assert "guest_token" not in data
    assert get_session(data["session_id"]).owner_user_id == user["id"]


def test_owner_other_user_and_admin(client, make_user, admin_headers):
    _, owner_headers = make_user("owner1")
    _, other_headers = make_user("intruder")
    session_id, _ = create_session(client, headers=owner_headers)

    assert client.get(f"/session/{session_id}", headers=owner_headers).status_code == 200
    assert client.get(f"/session/{session_id}", headers=other_headers).status_code == 404
    assert client.get(f"/session/{session_id}", headers=admin_headers).status_code == 200
    assert client.get(f"/session/{session_id}").status_code == 404


def test_guest_token_does_not_unlock_an_owned_session(client, make_user):
    _, owner_headers = make_user("owner1")
    session_id, _ = create_session(client, headers=owner_headers)
    _, guest_headers = create_session(client)
    assert client.get(f"/session/{session_id}", headers=guest_headers).status_code == 404


@pytest.mark.parametrize(
    "authorization",
    ["Bearer not-a-jwt", "Basic dXNlcjpwYXNz", "Bearer "],
)
def test_invalid_login_on_create_is_401_not_a_silent_guest(client, authorization):
    response = client.post("/session/new", json={"player_name": "X"}, headers={"Authorization": authorization})
    assert response.status_code == 401


def test_expired_login_on_create_is_401(client, monkeypatch):
    import auth
    monkeypatch.setattr(auth.config, "JWT_EXPIRATION_HOURS", -1)
    token = auth.create_access_token({"sub": "someone", "username": "x", "role": "player"})
    response = client.post("/session/new", json={}, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


# ─── Every route ───


@pytest.mark.parametrize(("method", "path", "body"), PROTECTED, ids=[f"{m} {p}" for m, p, _ in PROTECTED])
def test_every_session_route_requires_access(client, method, path, body):
    session_id, _ = create_session(client)
    response = _call(client, method, path.format(sid=session_id), body, {})
    assert response.status_code == 404
    assert get_session(session_id) is not None  # nothing was deleted or changed


def test_combat_init_endpoint_is_gone(client):
    session_id, headers = create_session(client)
    response = client.post(f"/session/{session_id}/combat/init?enemy_key=lich_king", headers=headers)
    assert response.status_code in (404, 405)


def test_owner_can_delete_and_non_owner_cannot(client, make_user):
    _, owner_headers = make_user("owner1")
    _, other_headers = make_user("intruder")
    session_id, _ = create_session(client, headers=owner_headers)

    assert client.delete(f"/session/{session_id}", headers=other_headers).status_code == 404
    assert client.get(f"/session/{session_id}", headers=owner_headers).status_code == 200

    assert client.delete(f"/session/{session_id}", headers=owner_headers).status_code == 200
    assert client.get(f"/session/{session_id}", headers=owner_headers).status_code == 404


# ─── Listing ───


def test_session_list_requires_login(client):
    assert client.get("/sessions").status_code == 401


def test_session_list_shows_only_your_sessions(client, make_user, admin_headers):
    _, alice = make_user("alice")
    _, bob = make_user("bob")
    alice_id, _ = create_session(client, headers=alice)
    bob_id, _ = create_session(client, headers=bob)
    guest_id, _ = create_session(client)

    alice_ids = {s["session_id"] for s in client.get("/sessions", headers=alice).json()}
    admin_ids = {s["session_id"] for s in client.get("/sessions", headers=admin_headers).json()}
    assert alice_ids == {alice_id}
    assert {alice_id, bob_id, guest_id} <= admin_ids


# ─── Responses and persistence ───


def test_ownership_fields_are_never_returned(client, make_user):
    _, headers = make_user("owner1")
    session_id, headers = create_session(client, headers=headers)
    body = client.get(f"/session/{session_id}", headers=headers).json()
    assert "owner_user_id" not in body and "guest_token_hash" not in body


def test_ownership_survives_a_reload_from_the_database(client, app_state, make_user):
    user, headers = make_user("owner1")
    session_id, _ = create_session(client, headers=headers)
    app_state.state_manager._sessions.clear()  # simulate a server restart

    assert client.get(f"/session/{session_id}/hydrate", headers=headers).status_code == 200
    assert get_session(session_id).owner_user_id == user["id"]


def test_guest_campaign_end_is_not_filed_under_admin(client, app_state):
    app_state.intent_parser.next_intent = make_intent(relevance="off_topic")
    session_id, headers = create_session(client)
    for _ in range(3):
        act(client, session_id, headers)

    admin = client.portal.call(app_state.db.get_user_by_username, "admin")
    history = client.portal.call(app_state.db.get_campaign_history, admin["id"])
    assert history == []


def test_logged_in_campaign_end_is_recorded_for_the_owner(client, app_state, make_user):
    user, user_headers = make_user("owner1")
    app_state.intent_parser.next_intent = make_intent(relevance="off_topic")
    session_id, headers = create_session(client, headers=user_headers)
    for _ in range(3):
        act(client, session_id, headers)

    history = client.portal.call(app_state.db.get_campaign_history, user["id"])
    assert [entry["session_id"] for entry in history] == [session_id]
    assert history[0]["character_class"] == "warrior"


# ─── Legacy data ───


def test_legacy_sessions_get_owners(tmp_path, monkeypatch):
    """Sessions saved before ownership existed: stored user if known, otherwise admin."""
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "legacy.db"))

    async def scenario():
        db = Database()
        await db.connect()
        admin = await db.create_user("admin", "x", "admin")
        player = await db.create_user("player", "x")
        with_user = GameSession(world_state={"user_id": player["id"]})
        stale_user = GameSession(world_state={"user_id": "deleted-account"})
        anonymous = GameSession(world_state={})
        for session in (with_user, stale_user, anonymous):
            await db.save_session(session)

        assert await db.backfill_session_owners(admin["id"]) == 3
        assert await db.backfill_session_owners(admin["id"]) == 0  # idempotent
        owners = {s.session_id: (await db.load_session(s.session_id)).owner_user_id
                  for s in (with_user, stale_user, anonymous)}
        await db.close()
        return admin["id"], player["id"], owners, (with_user, stale_user, anonymous)

    admin_id, player_id, owners, (with_user, stale_user, anonymous) = asyncio.run(scenario())
    assert owners[with_user.session_id] == player_id
    assert owners[stale_user.session_id] == admin_id
    assert owners[anonymous.session_id] == admin_id


def test_migration_adds_columns_to_an_old_database(tmp_path, monkeypatch):
    import sqlite3
    path = tmp_path / "old.db"
    conn = sqlite3.connect(path)
    conn.execute(
        "CREATE TABLE sessions (session_id TEXT PRIMARY KEY, player_id TEXT NOT NULL, player_name TEXT NOT NULL, "
        "player_json TEXT NOT NULL, world_state_json TEXT NOT NULL, turn_number INTEGER NOT NULL DEFAULT 0, "
        "created_at TEXT NOT NULL, updated_at TEXT NOT NULL)"
    )
    session = GameSession()
    conn.execute(
        "INSERT INTO sessions VALUES (?, ?, ?, ?, ?, 0, ?, ?)",
        (session.session_id, session.player.player_id, "Old", session.player.model_dump_json(),
         json.dumps({}), session.created_at.isoformat(), session.created_at.isoformat()),
    )
    conn.commit()
    conn.close()
    monkeypatch.setattr(database, "DB_PATH", str(path))

    async def scenario():
        db = Database()
        await db.connect()
        loaded = await db.load_session(session.session_id)
        await db.close()
        return loaded

    loaded = asyncio.run(scenario())
    assert loaded is not None and loaded.owner_user_id is None

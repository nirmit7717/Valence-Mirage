"""Bug 2 regressions: every combat-start path works and returns a consistent payload."""

import pytest

from helpers import act, create_session, get_session, make_intent, move_to_first_beat_of_type

GOBLIN_NARRATION = "A goblin scavenger lunges from the shadows, blade raised.\n→ Fight\n→ Dodge\n→ Shout"
NO_ENEMY_NARRATION = "The wind howls.\n→ Wait\n→ Listen\n→ Move on"
CRYPT_ENEMIES = {"Skeleton Soldier", "Undead Archer"}


def _prime_tension(session_id: str, *, location: str | None = None):
    """Put combat tension one point below the default threshold (6).

    Surprise fights only fit where the turn budget has room: the session must be on
    a story beat that isn't followed by a planned fight, outside the final act. In a
    Grand Saga that's the opening beat, so tension tests use campaign_size="large".
    """
    world = get_session(session_id).world_state
    world["combat_tension"] = 5
    if location:
        world["location"] = location


def _set_combat_beat(session_id: str):
    """Move the campaign to its first planned fight."""
    move_to_first_beat_of_type(session_id, "combat")


def _assert_combat_started(body: dict, session_id: str, expected_names: set[str]):
    assert body["combat_started"] is True
    combat_data = body["combat_data"]
    assert combat_data["combat_id"]
    assert combat_data["enemy"]["name"] in expected_names
    assert combat_data["enemy"]["hp"] == combat_data["enemy"]["max_hp"] > 0
    assert combat_data["player"]["max_hp"] > 0
    assert combat_data["abilities"], "class abilities should be included"
    assert body["pending_outcome"]["type"] == "combat_start"

    world = get_session(session_id).world_state
    assert world["combat"]["combat_id"] == combat_data["combat_id"]
    assert world["combat"]["enemy_key"]
    assert world["last_enemy_name"] == combat_data["enemy"]["name"]
    assert world["pending_combat"] is False
    assert world["combat_tension"] == 0


@pytest.mark.parametrize(
    ("requires_roll", "narration", "location", "expected"),
    [
        (False, GOBLIN_NARRATION, None, {"Goblin Scavenger"}),
        (False, NO_ENEMY_NARRATION, "An abandoned crypt beneath the chapel", CRYPT_ENEMIES),
        (True, GOBLIN_NARRATION, None, {"Goblin Scavenger"}),
        (True, NO_ENEMY_NARRATION, "An abandoned crypt beneath the chapel", CRYPT_ENEMIES),
    ],
    ids=["no-roll-narrator", "no-roll-fallback", "rolled-narrator", "rolled-fallback"],
)
def test_tension_threshold_starts_combat(client, app_state, fixed_roll, requires_roll, narration, location, expected):
    fixed_roll(5)
    # A side action (tangential) doesn't move the beat on, even when its roll succeeds,
    # so the beat stays open for the fight.
    app_state.intent_parser.next_intent = make_intent(
        requires_roll=requires_roll, description="inspect stonework", relevance="tangential"
    )
    session_id, headers = create_session(client, campaign_size="large")
    _prime_tension(session_id, location=location)
    app_state.narrator.text = narration

    response = act(client, session_id, headers)

    assert response.status_code == 200, response.text
    _assert_combat_started(response.json(), session_id, expected)


@pytest.mark.parametrize(
    ("narration", "location", "expected"),
    [
        (GOBLIN_NARRATION, None, {"Goblin Scavenger"}),
        (NO_ENEMY_NARRATION, "An abandoned crypt beneath the chapel", CRYPT_ENEMIES),
    ],
    ids=["beat-narrator", "beat-fallback"],
)
def test_combat_beat_starts_combat(client, app_state, fixed_roll, narration, location, expected):
    fixed_roll(5)
    app_state.intent_parser.next_intent = make_intent(requires_roll=True, description="inspect stonework")
    session_id, headers = create_session(client)
    _set_combat_beat(session_id)
    if location:
        get_session(session_id).world_state["location"] = location
    app_state.narrator.text = narration

    response = act(client, session_id, headers)

    assert response.status_code == 200, response.text
    _assert_combat_started(response.json(), session_id, expected)


def test_next_action_during_combat_returns_active_combat(client, app_state):
    app_state.intent_parser.next_intent = make_intent(description="inspect stonework")
    session_id, headers = create_session(client)
    _set_combat_beat(session_id)
    app_state.narrator.text = GOBLIN_NARRATION

    started = act(client, session_id, headers).json()
    follow_up = act(client, session_id, headers)

    assert follow_up.status_code == 200, follow_up.text
    body = follow_up.json()
    assert body["outcome"] == "combat_active"
    assert body["combat_data"]["combat_id"] == started["combat_data"]["combat_id"]
    assert body["combat_data"]["enemy"]["name"] == "Goblin Scavenger"
    assert body["combat_data"]["enemy_tier"] == 1

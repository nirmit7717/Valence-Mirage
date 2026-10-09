"""Bug: once the journey ended the campaign page got stuck.

The backend side: every ending records a result, ending responses carry no
story choices (so the card leads to the end screen), and hydrate tells a
refreshed page how the campaign ended.

New campaigns end when the final (boss) fight is won. Sessions saved before
turn budgets existed end on their last story beat — both paths are covered.
"""

import main
from engines import pacing
from helpers import (
    act,
    create_session,
    get_session,
    lose_fight,
    make_intent,
    move_to_beat,
    start_planned_fight,
    use_legacy_campaign,
    win_fight,
)


def _move_to_legacy_final_beat(session_id: str):
    """Old 9-beat campaign, positioned on its last (non-combat "climax") beat,
    with the turn counter where that beat's window opens on the next turn."""
    use_legacy_campaign(session_id)
    move_to_beat(session_id, -1)
    session = get_session(session_id)
    earliest, _ = pacing.beat_windows(session.world_state["campaign"])[-1]
    session.turn_number = earliest - 1


def _assert_victory_ending(body, session_id, client, headers):
    assert body["pending_outcome"] == {"type": "victory"}
    assert body["choices"] == []
    world = get_session(session_id).world_state
    assert world["campaign_ended"] is True
    assert world["campaign_result"] == "victory"

    hydrated = client.get(f"/session/{session_id}/hydrate", headers=headers).json()
    assert hydrated["campaign_ended"] is True
    assert hydrated["campaign_result"] == "victory"


def test_winning_the_final_fight_ends_in_victory_and_is_recorded(client, app_state):
    app_state.intent_parser.next_intent = make_intent(description="inspect stonework")
    app_state.narrator.text = "The tower's master steps from the shadows and attacks."
    session_id, headers = create_session(client)
    final_beat = move_to_beat(session_id, -1)
    assert final_beat["type"] == "combat" and final_beat["threat_hint"] == "boss"

    started = act(client, session_id, headers).json()
    assert started["combat_started"] is True
    body = win_fight(client, session_id, headers, started["combat_data"]).json()

    _assert_victory_ending(body, session_id, client, headers)
    assert get_session(session_id).world_state["campaign_saved"] is True


def test_legacy_rolled_final_beat_ends_in_victory(client, app_state, fixed_roll):
    fixed_roll(15)
    app_state.intent_parser.next_intent = make_intent(requires_roll=True, description="inspect stonework")
    session_id, headers = create_session(client)
    _move_to_legacy_final_beat(session_id)

    body = act(client, session_id, headers).json()

    _assert_victory_ending(body, session_id, client, headers)
    assert get_session(session_id).world_state["campaign_saved"] is True


def test_legacy_no_roll_final_beat_ends_in_victory(client, app_state):
    app_state.intent_parser.next_intent = make_intent(action_type="choice", description="make the final choice")
    session_id, headers = create_session(client)
    _move_to_legacy_final_beat(session_id)

    body = act(client, session_id, headers).json()

    _assert_victory_ending(body, session_id, client, headers)


def test_actions_after_the_end_are_rejected(client, app_state):
    app_state.intent_parser.next_intent = make_intent(action_type="choice")
    session_id, headers = create_session(client)
    _move_to_legacy_final_beat(session_id)
    act(client, session_id, headers)

    assert act(client, session_id, headers).status_code == 400


def test_combat_death_reports_defeat_on_hydrate(client, app_state):
    session_id, headers, combat_data = start_planned_fight(client, app_state)

    resolved = lose_fight(client, session_id, headers, combat_data).json()

    assert resolved["pending_outcome"]["type"] == "game_over"
    assert resolved["choices"] == []
    hydrated = client.get(f"/session/{session_id}/hydrate", headers=headers).json()
    assert hydrated["campaign_result"] == "defeat"


def test_combat_does_not_start_after_the_campaign_ends(client, app_state, fixed_roll):
    fixed_roll(15)
    app_state.intent_parser.next_intent = make_intent(requires_roll=True, description="inspect stonework")
    app_state.narrator.text = "A goblin scavenger lunges from the shadows."
    session_id, headers = create_session(client)
    _move_to_legacy_final_beat(session_id)
    get_session(session_id).world_state["combat_tension"] = 5

    body = act(client, session_id, headers).json()

    assert body["combat_started"] is False
    assert body["pending_outcome"] == {"type": "victory"}


def test_campaign_result_for_sessions_that_ended_before_it_existed():
    assert main._campaign_result({"campaign_result": "lost_focus"}) == "lost_focus"
    assert main._campaign_result({"status": "failed"}) == "defeat"
    assert main._campaign_result({"warning_count": 3}) == "lost_focus"
    assert main._campaign_result({}) == "victory"

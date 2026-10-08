"""Bug: once the journey ended the campaign page got stuck.

The backend side: every ending records a result, ending responses carry no
story choices (so the card leads to the end screen), and hydrate tells a
refreshed page how the campaign ended.
"""

import main
from helpers import act, create_session, get_session, make_intent


def _move_to_final_beat(session_id: str):
    """Fallback blueprint: act 3, beat 3 ("The Final Confrontation") is the last beat."""
    campaign = get_session(session_id).world_state["campaign"]
    campaign["current_act"] = 3
    campaign["current_beat"] = 3


def _assert_victory_ending(body, session_id, client, headers):
    assert body["pending_outcome"] == {"type": "victory"}
    assert body["choices"] == []
    world = get_session(session_id).world_state
    assert world["campaign_ended"] is True
    assert world["campaign_result"] == "victory"

    hydrated = client.get(f"/session/{session_id}/hydrate", headers=headers).json()
    assert hydrated["campaign_ended"] is True
    assert hydrated["campaign_result"] == "victory"


def test_rolled_final_beat_ends_in_victory_and_is_recorded(client, app_state, fixed_roll):
    fixed_roll(15)
    app_state.intent_parser.next_intent = make_intent(requires_roll=True, description="inspect stonework")
    session_id, headers = create_session(client)
    _move_to_final_beat(session_id)

    body = act(client, session_id, headers).json()

    _assert_victory_ending(body, session_id, client, headers)
    world = get_session(session_id).world_state
    assert world["campaign_saved"] is True  # rolled-path victories used to skip history


def test_no_roll_final_beat_ends_in_victory(client, app_state):
    app_state.intent_parser.next_intent = make_intent(action_type="choice", description="make the final choice")
    session_id, headers = create_session(client)
    _move_to_final_beat(session_id)

    body = act(client, session_id, headers).json()

    _assert_victory_ending(body, session_id, client, headers)


def test_actions_after_the_end_are_rejected(client, app_state):
    app_state.intent_parser.next_intent = make_intent(action_type="choice")
    session_id, headers = create_session(client)
    _move_to_final_beat(session_id)
    act(client, session_id, headers)

    assert act(client, session_id, headers).status_code == 400


def test_combat_death_reports_defeat_on_hydrate(client, app_state):
    app_state.intent_parser.next_intent = make_intent(description="inspect stonework")
    app_state.narrator.text = "A goblin scavenger lunges from the shadows."
    session_id, headers = create_session(client)
    get_session(session_id).world_state["combat_tension"] = 5
    started = act(client, session_id, headers).json()

    resolved = client.post(f"/session/{session_id}/combat/resolve", headers=headers, json={
        "combat_id": started["combat_data"]["combat_id"],
        "result": "defeat", "player_hp": 0, "player_mana": started["combat_data"]["player"]["mana"],
        "enemy_name": started["combat_data"]["enemy"]["name"], "combat_log": [], "turns_taken": 3,
    }).json()

    assert resolved["pending_outcome"]["type"] == "game_over"
    assert resolved["choices"] == []
    hydrated = client.get(f"/session/{session_id}/hydrate", headers=headers).json()
    assert hydrated["campaign_result"] == "defeat"


def test_combat_does_not_start_after_the_campaign_ends(client, app_state, fixed_roll):
    fixed_roll(15)
    app_state.intent_parser.next_intent = make_intent(requires_roll=True, description="inspect stonework")
    app_state.narrator.text = "A goblin scavenger lunges from the shadows."
    session_id, headers = create_session(client)
    _move_to_final_beat(session_id)
    get_session(session_id).world_state["combat_tension"] = 5

    body = act(client, session_id, headers).json()

    assert body["combat_started"] is False
    assert body["pending_outcome"] == {"type": "victory"}


def test_campaign_result_for_sessions_that_ended_before_it_existed():
    assert main._campaign_result({"campaign_result": "lost_focus"}) == "lost_focus"
    assert main._campaign_result({"status": "failed"}) == "defeat"
    assert main._campaign_result({"warning_count": 3}) == "lost_focus"
    assert main._campaign_result({}) == "victory"

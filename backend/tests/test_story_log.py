"""Hydrate returns the story so far, so a refreshed page can page back through it,
and the history endpoint returns full turn records for the campaign detail page."""

from helpers import act, create_session, make_intent


def test_story_log_has_the_opening_and_every_turn(client, app_state):
    session_id, headers = create_session(client)
    app_state.intent_parser.next_intent = make_intent(description="inspect stonework")
    app_state.narrator.text = "You study the carvings.\n→ Go on"
    act(client, session_id, headers, "I study the carvings")
    app_state.narrator.text = "A draft stirs the dust.\n→ Follow it"
    act(client, session_id, headers, "I follow the draft")

    log = client.get(f"/session/{session_id}/hydrate", headers=headers).json()["story_log"]

    assert [entry["turn"] for entry in log] == [0, 1, 2]
    assert log[0]["player_input"] is None
    assert log[1] == {"turn": 1, "player_input": "I study the carvings", "narration": "You study the carvings."}
    assert "→" not in log[2]["narration"]  # choice lines are stripped


def test_story_log_is_capped(client, app_state, monkeypatch):
    import main
    monkeypatch.setattr(main, "_STORY_LOG_LIMIT", 3)
    session_id, headers = create_session(client)
    app_state.intent_parser.next_intent = make_intent(description="inspect stonework")
    for i in range(5):
        assert act(client, session_id, headers, f"I search the room again ({i})").json()["redo_turn"] is False

    log = client.get(f"/session/{session_id}/hydrate", headers=headers).json()["story_log"]

    assert [entry["turn"] for entry in log] == [3, 4, 5]


def test_hydrate_reports_the_current_beat(client):
    session_id, headers = create_session(client)
    hydrated = client.get(f"/session/{session_id}/hydrate", headers=headers).json()
    assert hydrated["current_beat"] == "The Barkeep's Warning"


def test_history_returns_turn_records_with_outcome_objects(client, app_state):
    session_id, headers = create_session(client)
    app_state.intent_parser.next_intent = make_intent(description="inspect stonework")
    act(client, session_id, headers, "I look around")

    history = client.get(f"/session/{session_id}/history?limit=500", headers=headers).json()

    assert history[0]["player_input"] == "I look around"
    assert isinstance(history[0]["outcome"], dict)  # the detail page reads outcome.result / .narration
    assert history[0]["outcome"]["result"] == "narrative_choice"


def test_history_limit_is_bounded(client):
    session_id, headers = create_session(client)
    assert client.get(f"/session/{session_id}/history?limit=0", headers=headers).status_code == 422
    assert client.get(f"/session/{session_id}/history?limit=100000", headers=headers).status_code == 422

"""Bug 1 regressions: rolled actions complete and mana is deducted exactly once."""

import main
from helpers import act, create_session, get_session, make_intent, win_fight

COST = 10


def _expected_mana(start: int, max_mana: int, outcome: str, cost: int = COST) -> int:
    """Mirror the documented rules: one cost deduction, +5 on crit success, +1 regen unless crit failure."""
    delta = -cost + (5 if outcome == "critical_success" else 0)
    mana = max(0, min(max_mana, start + delta))
    if outcome != "critical_failure":
        mana = min(max_mana, mana + 1)
    return mana


def _rolled_intent(**overrides):
    data = {"requires_roll": True}
    data.update(overrides)
    return make_intent(**data)


def test_rolled_action_completes_and_persists(client, app_state, fixed_roll):
    fixed_roll(5)
    app_state.intent_parser.next_intent = _rolled_intent()
    session_id, headers = create_session(client)

    response = act(client, session_id, headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["requires_roll"] is True
    assert body["roll"] == 5
    assert body["dice_result"]["rolled"] == 5
    assert body["turn_number"] == 1

    history = client.get(f"/session/{session_id}/history", headers=headers)
    assert history.status_code == 200
    assert len(history.json()) == 1

    reloaded = client.portal.call(app_state.db.load_session, session_id)
    assert reloaded.turn_number == 1
    assert len(reloaded.turn_history) == 1


def test_rolled_action_deducts_mana_once(client, app_state, fixed_roll):
    fixed_roll(5)
    app_state.intent_parser.next_intent = _rolled_intent(uses_resource=True, resource_cost=COST)
    session_id, headers = create_session(client)
    player = get_session(session_id).player
    start, max_mana = player.mana, player.max_mana

    body = act(client, session_id, headers).json()

    assert body["player_mana"] == _expected_mana(start, max_mana, body["outcome"])


def test_rolled_crit_success_refund_applies_once(client, app_state, fixed_roll):
    fixed_roll(20)
    app_state.intent_parser.next_intent = _rolled_intent(uses_resource=True, resource_cost=COST)
    session_id, headers = create_session(client)
    player = get_session(session_id).player
    start, max_mana = player.mana, player.max_mana

    body = act(client, session_id, headers).json()

    assert body["outcome"] == "critical_success"
    assert body["player_mana"] == _expected_mana(start, max_mana, "critical_success")


def test_no_roll_action_deducts_mana_once(client, app_state):
    app_state.intent_parser.next_intent = make_intent(uses_resource=True, resource_cost=COST)
    session_id, headers = create_session(client)
    player = get_session(session_id).player
    start, max_mana = player.mana, player.max_mana

    body = act(client, session_id, headers).json()

    assert body["outcome"] == "narrative_choice"
    assert body["player_mana"] == _expected_mana(start, max_mana, "narrative_choice")


def test_engagement_tracker_records_mana_spent(client, app_state, fixed_roll):
    fixed_roll(20)  # critical success refunds 5 mana but the spend is still the full cost
    app_state.intent_parser.next_intent = _rolled_intent(uses_resource=True, resource_cost=COST)
    session_id, headers = create_session(client)

    act(client, session_id, headers)

    signals = app_state.engagement_tracker._signals[session_id]
    assert len(signals) == 1
    assert signals[0].resources_spent == COST
    assert signals[0].required_roll is True


def test_state_persists_across_turns(client, app_state, fixed_roll):
    fixed_roll(5)
    app_state.intent_parser.next_intent = _rolled_intent(uses_resource=True, resource_cost=COST)
    session_id, headers = create_session(client)
    player = get_session(session_id).player
    start, max_mana = player.mana, player.max_mana

    first = act(client, session_id, headers).json()
    second = act(client, session_id, headers).json()

    after_first = _expected_mana(start, max_mana, first["outcome"])
    assert first["player_mana"] == after_first
    assert second["player_mana"] == _expected_mana(after_first, max_mana, second["outcome"])
    assert second["turn_number"] == 2

    reloaded = client.portal.call(app_state.db.load_session, session_id)
    assert reloaded.player.mana == second["player_mana"]


def test_sessions_do_not_interfere(client, app_state, fixed_roll):
    fixed_roll(5)
    app_state.intent_parser.next_intent = _rolled_intent()
    first_id, first_headers = create_session(client, player_name="Player1")
    second_id, second_headers = create_session(client, player_name="Player2")

    assert act(client, first_id, first_headers).status_code == 200
    assert act(client, second_id, second_headers, "I explore the cave").status_code == 200

    first = client.get(f"/session/{first_id}", headers=first_headers).json()
    second = client.get(f"/session/{second_id}", headers=second_headers).json()
    assert first["player"]["name"] == "Player1"
    assert second["player"]["name"] == "Player2"
    assert first["turn_number"] == 1
    assert second["turn_number"] == 1


def test_history_returns_each_turn(client, app_state, fixed_roll):
    fixed_roll(5)
    app_state.intent_parser.next_intent = _rolled_intent()
    session_id, headers = create_session(client)

    act(client, session_id, headers, "I look around")
    act(client, session_id, headers, "I examine the barkeep")

    history = client.get(f"/session/{session_id}/history", headers=headers).json()
    assert [turn["player_input"] for turn in history] == ["I look around", "I examine the barkeep"]


def test_repeated_actions_do_not_get_easier(client, app_state, fixed_roll):
    # Keep failing (roll 1) with a non-hostile action type so tension doesn't start
    # surprise fights. The turn budget still forces beats on, so planned fights are won.
    fixed_roll(1)
    # The description avoids words shared with beat text (no narrative-alignment bonus).
    app_state.intent_parser.next_intent = _rolled_intent(action_type="investigate", description="inspect stonework")
    session_id, headers = create_session(client)

    probabilities = []
    for _ in range(5):
        response = act(client, session_id, headers, "I search the wall")
        assert response.status_code == 200, response.text
        body = response.json()
        probabilities.append(body["probability"])
        if body["combat_started"]:  # the turn budget brings planned fights in; get past them
            assert win_fight(client, session_id, headers, body["combat_data"]).status_code == 200

    assert probabilities[-1] <= probabilities[0] + 0.05


def test_compute_state_changes_charges_cost_once():
    changes = main._compute_state_changes(_rolled_intent(uses_resource=True, resource_cost=COST), "success", 12)
    assert changes.mana_delta == -COST

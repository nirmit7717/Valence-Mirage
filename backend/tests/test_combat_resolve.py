"""Bug 4: combat results from the browser are checked against the stored encounter.

Also covers: used consumables leave the server inventory, ability targets reach
the client, and a refresh mid-fight gets the same fight back.
"""

import pytest

from helpers import create_session, get_session, start_planned_fight
from models.character import CLASS_ABILITIES, CharacterClass


def _start_fight(client, app_state, **session_body):
    return start_planned_fight(client, app_state, **session_body)


def _resolve(client, session_id, headers, combat, **overrides):
    body = {
        "combat_id": combat["combat_id"],
        "result": "victory",
        "player_hp": combat["player"]["hp"],
        "player_mana": combat["player"]["mana"],
        "enemy_name": combat["enemy"]["name"],
        "items_used": [],
        "combat_log": [],
        "turns_taken": 4,
    }
    body.update(overrides)
    return client.post(f"/session/{session_id}/combat/resolve", headers=headers, json=body)


# ─── Happy path ───


def test_valid_victory_awards_the_stored_encounters_xp(client, app_state):
    session_id, headers, combat = _start_fight(client, app_state)
    expected_xp = get_session(session_id).world_state["combat"]["xp_reward"]

    response = _resolve(client, session_id, headers, combat, player_hp=combat["player"]["hp"] - 5)

    assert response.status_code == 200, response.text
    assert response.json()["rewards"]["xp"] == expected_xp > 0
    session = get_session(session_id)
    assert session.player.hp == combat["player"]["hp"] - 5
    assert "combat" not in session.world_state


def test_defeat_at_zero_hp_is_accepted(client, app_state):
    session_id, headers, combat = _start_fight(client, app_state)
    response = _resolve(client, session_id, headers, combat, result="defeat", player_hp=0)
    assert response.status_code == 200
    assert response.json()["pending_outcome"]["type"] == "game_over"


# ─── Replays and stale fights ───


def test_the_same_result_cannot_be_claimed_twice(client, app_state):
    session_id, headers, combat = _start_fight(client, app_state)
    assert _resolve(client, session_id, headers, combat).status_code == 200

    replay = _resolve(client, session_id, headers, combat)

    assert replay.status_code == 409


def test_no_active_combat_is_409(client, app_state):
    session_id, headers = create_session(client)
    fake = {"combat_id": "made-up", "enemy": {"name": "Lich King"}, "player": {"hp": 10, "mana": 10}}
    assert _resolve(client, session_id, headers, fake).status_code == 409


def test_wrong_combat_id_is_409(client, app_state):
    session_id, headers, combat = _start_fight(client, app_state)
    assert _resolve(client, session_id, headers, combat, combat_id="someone-elses-fight").status_code == 409
    assert "combat" in get_session(session_id).world_state  # nothing changed


# ─── Forged values ───


def test_enemy_mismatch_is_400(client, app_state):
    session_id, headers, combat = _start_fight(client, app_state)
    assert _resolve(client, session_id, headers, combat, enemy_name="Ancient Dragon").status_code == 400


@pytest.mark.parametrize(
    "overrides",
    [{"result": "fled"}, {"player_hp": -1}, {"player_mana": -5}, {"turns_taken": 0}, {"turns_taken": 999},
     {"combat_id": ""}, {"items_used": ["Health Potion"] * 21}],
    ids=["bad-result", "negative-hp", "negative-mana", "zero-turns", "too-many-turns", "empty-id", "too-many-items"],
)
def test_malformed_results_are_422(client, app_state, overrides):
    session_id, headers, combat = _start_fight(client, app_state)
    assert _resolve(client, session_id, headers, combat, **overrides).status_code == 422


def test_defeat_with_hp_left_is_400(client, app_state):
    session_id, headers, combat = _start_fight(client, app_state)
    assert _resolve(client, session_id, headers, combat, result="defeat", player_hp=10).status_code == 400


def test_hp_above_maximum_is_400(client, app_state):
    session_id, headers, combat = _start_fight(client, app_state)
    assert _resolve(client, session_id, headers, combat, player_hp=combat["player"]["max_hp"] + 1).status_code == 400


def test_mana_above_what_was_possible_is_400(client, app_state):
    session_id, headers, combat = _start_fight(client, app_state, character_class="wizard")
    session = get_session(session_id)
    session.player.mana = 20  # fight starts low on mana
    session.world_state["combat"]["start_mana"] = 20
    assert _resolve(client, session_id, headers, combat, player_mana=60).status_code == 400


def test_restoring_items_raise_the_mana_allowance_and_are_removed(client, app_state):
    session_id, headers, combat = _start_fight(client, app_state, character_class="wizard")
    session = get_session(session_id)
    session.player.mana = 20
    session.world_state["combat"]["start_mana"] = 20
    crystals_before = sum(1 for i in session.player.inventory if i.name == "Mana Crystal")

    response = _resolve(client, session_id, headers, combat, player_mana=40, items_used=["Mana Crystal"])

    assert response.status_code == 200, response.text
    crystals_after = sum(1 for i in get_session(session_id).player.inventory if i.name == "Mana Crystal")
    assert crystals_after == crystals_before - 1
    names = [item["name"] for item in response.json()["inventory"]]
    assert names.count("Mana Crystal") == crystals_before - 1


def test_items_not_in_the_inventory_are_400(client, app_state):
    session_id, headers, combat = _start_fight(client, app_state)
    assert _resolve(client, session_id, headers, combat, items_used=["Elixir of Immortality"]).status_code == 400


def test_using_more_copies_than_carried_is_400(client, app_state):
    session_id, headers, combat = _start_fight(client, app_state)
    carried = sum(1 for i in get_session(session_id).player.inventory if i.name == "Health Potion")
    response = _resolve(client, session_id, headers, combat, items_used=["Health Potion"] * (carried + 1))
    assert response.status_code == 400


def test_weapons_cannot_be_reported_as_used_consumables(client, app_state):
    session_id, headers, combat = _start_fight(client, app_state)
    assert _resolve(client, session_id, headers, combat, items_used=["Iron Sword"]).status_code == 400


def test_a_boss_cannot_be_beaten_in_one_turn(client, app_state):
    session_id, headers, combat = _start_fight(client, app_state)
    stored = get_session(session_id).world_state["combat"]
    stored["enemies"][0]["hp"] = stored["enemies"][0]["max_hp"] = 300

    assert _resolve(client, session_id, headers, combat, turns_taken=1).status_code == 400
    assert _resolve(client, session_id, headers, combat, turns_taken=20).status_code == 200


# ─── Ability targets (Task 8) ───


def test_debuff_abilities_target_the_enemy():
    by_name = {a.name: a for abilities in CLASS_ABILITIES.values() for a in abilities}
    assert by_name["War Cry"].target == "enemy"
    assert by_name["Lullaby"].target == "enemy"
    assert by_name["Guard"].target == "self"
    assert by_name["Power Strike"].target == "enemy"  # attacks always target the enemy


def test_a_one_turn_stun_skips_the_enemys_next_turn():
    from engines.combat_engine import CombatEngine
    from engines.state_manager import StateManager

    engine = CombatEngine()
    combat = engine.initiate_combat(StateManager().create_session("Bard").player, enemy_key="bandit_thug")
    engine._apply_effect(combat.enemies[0], "stun", 1)
    hp_before = combat.player.hp

    engine.resolve_enemy_action(combat)

    assert combat.log[-1].action == "Stunned"
    assert combat.player.hp == hp_before
    assert combat.enemies[0].status_effects == []  # and the stun is used up


def test_combat_payload_sends_ability_targets(client, app_state):
    _, _, combat = _start_fight(client, app_state, character_class="bard")
    targets = {a["name"]: a["target"] for a in combat["abilities"]}
    assert targets["Lullaby"] == "enemy"
    assert targets["Inspire"] == "self"


def test_old_sessions_get_current_ability_rules(client, app_state):
    session_id, headers, _ = _start_fight(client, app_state, character_class="warrior")
    session = get_session(session_id)
    session.world_state["abilities"] = [
        {k: v for k, v in a.model_dump().items() if k != "target"}
        for a in CLASS_ABILITIES[CharacterClass.WARRIOR]
    ]

    hydrated = client.get(f"/session/{session_id}/hydrate", headers=headers).json()

    war_cry = next(a for a in hydrated["combat_data"]["abilities"] if a["name"] == "War Cry")
    assert war_cry["target"] == "enemy"


# ─── Refresh mid-fight (Task 9) ───


def test_hydrate_returns_the_active_fight(client, app_state):
    session_id, headers, combat = _start_fight(client, app_state)

    hydrated = client.get(f"/session/{session_id}/hydrate", headers=headers).json()

    assert hydrated["combat_data"]["combat_id"] == combat["combat_id"]
    assert hydrated["combat_data"]["enemy"]["name"] == combat["enemy"]["name"]
    assert _resolve(client, session_id, headers, hydrated["combat_data"]).status_code == 200
    after = client.get(f"/session/{session_id}/hydrate", headers=headers).json()
    assert after["combat_data"] is None


def test_hydrate_has_no_fight_when_none_is_active(client):
    session_id, headers = create_session(client)
    assert client.get(f"/session/{session_id}/hydrate", headers=headers).json()["combat_data"] is None

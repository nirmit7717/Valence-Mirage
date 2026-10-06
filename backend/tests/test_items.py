"""Item normalization: class gear and loot bonuses/effects must reach the Item model."""

import random

import pytest

from data.enemies import ENEMY_TEMPLATES
from data.items import item_from_definition
from engines.combat_engine import CombatEngine
from engines.state_manager import StateManager
from helpers import act, create_session, get_session, make_intent
from models.combat import CombatState


def test_top_level_armor_bonus_moves_into_stat_bonus():
    item = item_from_definition({"name": "Wooden Shield", "type": "armor", "armor_bonus": 2})
    assert item.item_type == "armor"
    assert item.stat_bonus == {"armor_bonus": 2}


def test_damage_bonus_and_existing_stat_bonus_are_merged():
    item = item_from_definition(
        {"name": "Odd Blade", "type": "weapon", "damage_bonus": 3, "stat_bonus": {"strength": 1}}
    )
    assert item.stat_bonus == {"strength": 1, "damage_bonus": 3}


@pytest.mark.parametrize(
    ("effect", "hp", "mana"),
    [("heal_20", 20, 0), ("heal_15", 15, 0), ("mana_20", 0, 20)],
)
def test_consumable_effect_strings_become_restore_values(effect, hp, mana):
    item = item_from_definition({"name": "Tonic", "type": "consumable", "effect": effect})
    assert item.hp_restore == hp
    assert item.mana_restore == mana
    assert item.consumes_on_use is True


def test_explicit_restore_keys_are_honored():
    item = item_from_definition({"name": "Small Health Potion", "type": "consumable", "hp_restore": 15})
    assert item.hp_restore == 15
    assert item.consumes_on_use is True


def test_unknown_effect_is_ignored():
    item = item_from_definition({"name": "Smoke Bomb", "type": "consumable", "effect": "hidden_2"})
    assert item.hp_restore == 0
    assert item.mana_restore == 0


def test_description_defaults_and_overrides():
    assert item_from_definition({"name": "Rock"}, description="Found nearby").description == "Found nearby"
    assert item_from_definition({"name": "Rock", "description": "A rock"}, description="x").description == "A rock"
    assert item_from_definition({"name": "Rock"}).item_type == "misc"


def test_combat_rewards_produce_normalized_loot():
    engine = CombatEngine()
    engine.rng = random.Random(0)
    engine.rng.random = lambda: 0.0  # every loot entry drops
    combat = engine.initiate_combat(StateManager().create_session("Loot").player, enemy_key="dragon_whelp")
    combat.status = "victory"

    rewards = engine.get_combat_rewards(combat)

    by_name = {item.name: item for item in rewards["items"]}
    assert rewards["xp"] == ENEMY_TEMPLATES["dragon_whelp"].xp_reward
    assert by_name["Dragon Scale"].stat_bonus["armor_bonus"] == 4
    assert by_name["Dragon Tooth"].stat_bonus["damage_bonus"] == 4
    assert by_name["Superior Health Potion"].hp_restore == 60
    assert by_name["Superior Health Potion"].consumes_on_use is True


def _start_forced_combat(client, app_state, character_class: str) -> dict:
    app_state.intent_parser.next_intent = make_intent(description="inspect stonework")
    app_state.narrator.text = "A goblin scavenger lunges from the shadows."
    session_id, headers = create_session(client, character_class=character_class)
    get_session(session_id).world_state["combat_tension"] = 5
    body = act(client, session_id, headers).json()
    assert body["combat_started"] is True
    return body["combat_data"]


@pytest.mark.parametrize(("character_class", "armor"), [("warrior", 2), ("rogue", 1), ("cleric", 3), ("wizard", 0)])
def test_class_armor_counts_in_combat(client, app_state, character_class, armor):
    combat_data = _start_forced_combat(client, app_state, character_class)
    assert combat_data["player"]["armor"] == armor


def test_class_consumables_are_usable_in_combat(client, app_state):
    combat_data = _start_forced_combat(client, app_state, "warrior")
    restores = [item["hp_restore"] for item in combat_data["inventory"] if item["name"] == "Health Potion"]
    assert 20 in restores


def test_wizard_mana_crystal_restores_mana(client, app_state):
    combat_data = _start_forced_combat(client, app_state, "wizard")
    crystal = next(item for item in combat_data["inventory"] if item["name"] == "Mana Crystal")
    assert crystal["type"] == "consumable"
    assert crystal["mana_restore"] == 20


def test_session_inventory_stores_class_gear_bonuses(client):
    session_id, _ = create_session(client, character_class="warrior")
    shield = next(item for item in get_session(session_id).player.inventory if item.name == "Wooden Shield")
    assert shield.stat_bonus["armor_bonus"] == 2


def test_combat_state_round_trips_enemy_key():
    combat = CombatEngine().initiate_combat(StateManager().create_session("Key").player, enemy_tier=2)
    restored = CombatState(**combat.model_dump())
    assert restored.enemy_key in ENEMY_TEMPLATES
    assert ENEMY_TEMPLATES[restored.enemy_key].name == restored.enemies[0].name

"""Enemy effects that actually work.

Every status an ability can apply exists in the effect registry (old names like
"bleeding" or "blessed" used to do nothing), self-buffs land on the enemy, the
new ``empowered`` effect raises damage, and the browser's registry matches the
server's.
"""

import random
import re
from pathlib import Path

import pytest

from data.enemies import ENEMY_TEMPLATES
from data.enemy_archetypes import ARCHETYPE_PRESETS, build_enemy_template
from engines.combat_engine import CombatEngine
from engines.state_manager import StateManager
from helpers import get_session, start_planned_fight
from models.character import CLASS_ABILITIES
from models.combat import STATUS_EFFECT_RULES, StatusEffect, canonical_status, get_effect_rule

FRONTEND_COMBAT = Path(__file__).resolve().parents[2] / "frontend" / "src" / "utils" / "combatRules.js"
REGISTRY = {str(getattr(name, "value", name)) for name in STATUS_EFFECT_RULES}


def _effects(abilities) -> set[str]:
    return {a["status_effect"] for a in abilities if a.get("status_effect")}


# ─── Every effect in use exists ───


def test_class_ability_effects_exist():
    used = {a.status_effect for abilities in CLASS_ABILITIES.values() for a in abilities if a.status_effect}
    assert used <= REGISTRY, used - REGISTRY


def test_enemy_template_effects_exist():
    used = set().union(*(_effects(t.abilities) for t in ENEMY_TEMPLATES.values()))
    assert used <= REGISTRY, used - REGISTRY


@pytest.mark.parametrize("archetype", ARCHETYPE_PRESETS)
def test_archetype_effects_exist(archetype):
    used = _effects(ARCHETYPE_PRESETS[archetype]["moves"])
    used |= _effects(build_enemy_template("Foe", archetype, "boss", 3).abilities)
    assert used <= REGISTRY, used - REGISTRY


def test_enemy_ability_targets_are_valid():
    abilities = [a for t in ENEMY_TEMPLATES.values() for a in t.abilities]
    abilities += [m for preset in ARCHETYPE_PRESETS.values() for m in preset["moves"]]
    assert {a.get("target", "player") for a in abilities} <= {"player", "self"}


# ─── The browser runs the same rules ───


def _frontend_block(name: str) -> str:
    source = FRONTEND_COMBAT.read_text(encoding="utf-8")
    match = re.search(rf"{name}\s*=\s*\{{(.*?)\n\s*\}};", source, re.DOTALL)
    assert match, f"{name} not found in {FRONTEND_COMBAT}"
    return match.group(1)


def test_frontend_and_backend_registries_list_the_same_effects():
    frontend = set(re.findall(r"^\s*(\w+):\s*\{", _frontend_block("STATUS_RULES"), re.MULTILINE))
    assert frontend == REGISTRY


def test_every_effect_has_an_icon_in_the_browser():
    icons = set(re.findall(r"(\w+):\s*'", _frontend_block("STATUS_ICONS")))
    assert REGISTRY <= icons, REGISTRY - icons


# ─── Empowered and old names ───


def test_empowered_raises_damage_for_two_turns_at_most():
    rule = get_effect_rule("empowered")
    assert rule["damage_modifier"] == 1.5
    assert rule["max_duration"] == 2


@pytest.mark.parametrize(
    ("old", "current"),
    [("bleeding", "bleed"), ("stunned", "stun"), ("weakened", "weaken"), ("frightened", "weaken"),
     ("blessed", "empowered"), ("Bleed", "bleed"), ("focus", "focus")],
)
def test_old_effect_names_map_to_current_ones(old, current):
    assert canonical_status(old) == current
    assert get_effect_rule(old) == get_effect_rule(current)


def test_rage_abilities_empower_the_enemy_itself():
    for key, name in (("vampire_lord", "Blood Frenzy"), ("ancient_dragon", "Ancient Rage")):
        ability = next(a for a in ENEMY_TEMPLATES[key].abilities if a["name"] == name)
        assert (ability["status_effect"], ability["target"]) == ("empowered", "self")


# ─── The server-side engine ───


class _Rigged(random.Random):
    """Always hits (roll 15), never dodges, never takes the 30% random-ability branch."""

    def randint(self, a, b):
        return 15 if (a, b) == (1, 20) else a

    def random(self):
        return 0.99

    def choice(self, seq):
        return seq[0]


def _fight(enemy_key: str, abilities: list[dict]):
    engine = CombatEngine()
    engine.rng = _Rigged()
    combat = engine.initiate_combat(StateManager().create_session("Warrior").player, enemy_key=enemy_key)
    enemy = combat.enemies[0]
    enemy.abilities = abilities
    enemy.hp = enemy.max_hp // 3  # below half: the enemy reaches for its abilities
    return engine, combat


def test_a_self_buff_lands_on_the_enemy_and_skips_the_attack():
    frenzy = {"name": "Blood Frenzy", "status_effect": "empowered", "status_duration": 3, "target": "self"}
    engine, combat = _fight("vampire_lord", [frenzy])
    hp_before = combat.player.hp

    engine.resolve_enemy_action(combat)

    assert [e.name for e in combat.enemies[0].status_effects] == ["empowered"]
    assert combat.enemies[0].status_effects[0].duration == 2  # capped
    assert combat.player.status_effects == []
    assert combat.player.hp == hp_before
    assert combat.log[-1].action == "Blood Frenzy"


def test_empowered_enemies_hit_harder():
    engine, combat = _fight("bandit_thug", [])
    enemy = combat.enemies[0]
    assert engine._get_damage_modifier(enemy) == 1.0
    enemy.status_effects.append(StatusEffect(name="empowered", duration=2))
    assert engine._get_damage_modifier(enemy) == 1.5


def test_a_status_only_move_applies_its_effect_without_damage():
    hex_move = {"name": "Hex", "status_effect": "weaken", "status_duration": 2}
    engine, combat = _fight("shadow_mage", [hex_move])
    hp_before = combat.player.hp

    engine.resolve_enemy_action(combat)

    assert combat.player.hp == hp_before
    assert [e.name for e in combat.player.status_effects] == ["weaken"]


def test_old_effect_names_still_work_in_the_engine():
    engine, combat = _fight("dark_knight", [])
    engine._apply_effect(combat.player, "stunned", 1)
    assert [e.name for e in combat.player.status_effects] == ["stun"]
    assert engine._can_act(combat.player) is False


# ─── What the browser receives ───


def test_the_combat_payload_sends_current_effect_names_and_targets(client, app_state):
    session_id, headers, _ = start_planned_fight(client, app_state)
    stored = get_session(session_id).world_state["combat"]["enemies"][0]
    stored["abilities"] = [  # saved before the effect names were fixed
        {"name": "Savage Bite", "damage_dice": "2d6+3", "status_effect": "bleeding", "status_duration": 2},
        {"name": "Blood Frenzy", "status_effect": "blessed", "status_duration": 3},
    ]

    enemy = client.get(f"/session/{session_id}/hydrate", headers=headers).json()["combat_data"]["enemy"]

    assert [(a["status_effect"], a["target"]) for a in enemy["abilities"]] == [
        ("bleed", "player"), ("empowered", "self"),
    ]

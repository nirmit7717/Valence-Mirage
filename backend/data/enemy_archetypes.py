"""Enemy archetype presets.

An enemy's name comes from the campaign (what the narrator described); its
numbers come from a preset chosen by *how* it was described: its archetype
(brute, construct, caster...) and threat level (minion, standard, elite, boss),
scaled by tier (how far the story has come, see engines/progression.py).
Baselines are calibrated against the hand-built templates in data/enemies.py.
"""

from engines.progression import fight_xp
from models.combat import EnemyTemplate

ARCHETYPES = ("brute", "soldier", "skirmisher", "beast", "caster", "construct", "undead", "horror")
THREATS = ("minion", "standard", "elite", "boss")

# XP isn't here: every enemy is worth progression.fight_xp(tier, threat).
TIER_BASE = {
    1: {"hp": 16, "armor": 1, "attack_bonus": 1.5},
    2: {"hp": 24, "armor": 2, "attack_bonus": 2.5},
    3: {"hp": 38, "armor": 3, "attack_bonus": 3.0},
    4: {"hp": 55, "armor": 5, "attack_bonus": 4.5},
    5: {"hp": 85, "armor": 6, "attack_bonus": 6.5},
}

# Damage ladder; tiers start at a step and archetypes/moves shift along it.
DAMAGE_STEPS = ("1d4+1", "1d6+1", "1d8+2", "1d10+3", "2d8+3", "2d10+4", "3d8+6", "3d10+7", "4d10+8")
TIER_DAMAGE_STEP = {1: 1, 2: 2, 3: 3, 4: 5, 5: 6}

# hp: multiplier, armor/attack: flat deltas, damage: ladder offset.
# Moves use status names from the canonical registry (models/combat.py).
ARCHETYPE_PRESETS: dict[str, dict] = {
    "brute": {
        "hp": 1.35, "armor": 1, "attack": -0.5, "damage": 1,
        "moves": [
            {"name": "Crushing Blow", "damage": 1, "status_effect": "stun", "status_duration": 1},
            {"name": "Rampage", "damage": 2},
        ],
    },
    "soldier": {
        "hp": 1.0, "armor": 1, "attack": 0.0, "damage": 0,
        "moves": [
            {"name": "Precise Strike", "damage": 1},
            {"name": "Suppressing Assault", "damage": 0, "status_effect": "weaken", "status_duration": 2},
        ],
    },
    "skirmisher": {
        "hp": 0.8, "armor": -1, "attack": 1.0, "damage": 0,
        "moves": [
            {"name": "Vicious Cut", "damage": 0, "status_effect": "bleed", "status_duration": 2},
            {"name": "Flurry of Blows", "damage": 1},
        ],
    },
    "beast": {
        "hp": 0.9, "armor": -1, "attack": 0.5, "damage": 0,
        "moves": [
            {"name": "Savage Bite", "damage": 1, "status_effect": "bleed", "status_duration": 2},
            {"name": "Pounce", "damage": 0, "status_effect": "stun", "status_duration": 1},
        ],
    },
    "caster": {
        "hp": 0.75, "armor": -1, "attack": 1.0, "damage": 1,
        "moves": [
            {"name": "Searing Blast", "damage": 1, "status_effect": "burning", "status_duration": 2},
            {"name": "Hex", "damage": None, "status_effect": "weaken", "status_duration": 2},
        ],
    },
    "construct": {
        "hp": 1.1, "armor": 2, "attack": 0.0, "damage": 0,
        "moves": [
            {"name": "Shock Pulse", "damage": 0, "status_effect": "stun", "status_duration": 1},
            {"name": "Overcharged Strike", "damage": 2},
        ],
    },
    "undead": {
        "hp": 1.0, "armor": 0, "attack": 0.0, "damage": 0,
        "moves": [
            {"name": "Draining Touch", "damage": 0, "heal_self": True},
            {"name": "Grave Rot", "damage": None, "status_effect": "poisoned", "status_duration": 3},
        ],
    },
    "horror": {
        "hp": 1.25, "armor": 0, "attack": 0.5, "damage": 1,
        "moves": [
            {"name": "Dread Gaze", "damage": None, "status_effect": "weaken", "status_duration": 2},
            {"name": "Rend", "damage": 1, "status_effect": "bleed", "status_duration": 2},
        ],
    },
}

THREAT_MODIFIERS = {
    "minion": {"hp": 0.7, "armor": -1, "attack": -0.5},
    "standard": {"hp": 1.0, "armor": 0, "attack": 0.0},
    "elite": {"hp": 1.35, "armor": 1, "attack": 0.5},
    "boss": {"hp": 1.8, "armor": 2, "attack": 1.0},
}

# Loot names per genre: (healing, mana restore, armor drop).
_LOOT_NAMES = {
    "fantasy": ("Healing Draught", "Mana Draught", "Salvaged Armor"),
    "scifi": ("Med Injector", "Focus Stim", "Salvaged Armor Plating"),
    "postapoc": ("Scavenged Medkit", "Focus Tonic", "Scrap Armor"),
}
_HEAL_BY_TIER = {1: 15, 2: 25, 3: 40, 4: 60, 5: 80}


def _clamp_tier(tier: int) -> int:
    return max(1, min(5, int(tier)))


def _damage(step: int) -> str:
    return DAMAGE_STEPS[max(0, min(len(DAMAGE_STEPS) - 1, step))]


def build_loot_table(tier: int, threat: str, genre: str = "fantasy") -> list[dict]:
    tier = _clamp_tier(tier)
    heal_name, mana_name, armor_name = _LOOT_NAMES.get(genre, _LOOT_NAMES["fantasy"])
    heal = _HEAL_BY_TIER[tier]
    table = [
        {"name": heal_name, "type": "consumable", "chance": 0.35, "hp_restore": heal},
        {"name": mana_name, "type": "consumable", "chance": 0.2, "mana_restore": max(15, heal // 2 + 5)},
    ]
    if threat in ("elite", "boss"):
        table.append({
            "name": armor_name, "type": "armor",
            "chance": 0.5 if threat == "boss" else 0.25,
            "armor_bonus": 1 + tier // 2,
        })
    return table


def build_enemy_template(
    name: str,
    archetype: str,
    threat: str = "standard",
    tier: int = 1,
    move_names: list[str] | None = None,
    genre: str = "fantasy",
) -> EnemyTemplate:
    """Create an enemy template whose stats follow from archetype, threat and tier."""
    archetype = archetype if archetype in ARCHETYPE_PRESETS else "soldier"
    threat = threat if threat in THREAT_MODIFIERS else "standard"
    tier = _clamp_tier(tier)

    base = TIER_BASE[tier]
    preset = ARCHETYPE_PRESETS[archetype]
    mod = THREAT_MODIFIERS[threat]
    step = TIER_DAMAGE_STEP[tier] + preset["damage"]

    hp = max(6, round(base["hp"] * preset["hp"] * mod["hp"]))
    armor = max(0, base["armor"] + preset["armor"] + mod["armor"])
    attack_bonus = max(0.0, round(base["attack_bonus"] + preset["attack"] + mod["attack"], 1))

    flavor = [m for m in (move_names or []) if m]
    abilities = []
    for index, move in enumerate(preset["moves"]):
        ability = {"name": flavor[index] if index < len(flavor) else move["name"]}
        if move.get("damage") is not None:
            ability["damage_dice"] = _damage(step + move["damage"])
        if move.get("status_effect"):
            ability["status_effect"] = move["status_effect"]
            ability["status_duration"] = move["status_duration"]
        if move.get("heal_self"):
            ability["heal_self"] = True
        abilities.append(ability)
    if threat == "boss":
        finisher = flavor[2] if len(flavor) > 2 else "Devastating Onslaught"
        abilities.append({"name": finisher, "damage_dice": _damage(step + 3)})

    return EnemyTemplate(
        name=name,
        tier=tier,
        hp=hp,
        armor=armor,
        attack_bonus=attack_bonus,
        damage_dice=_damage(step),
        abilities=abilities,
        loot_table=build_loot_table(tier, threat, genre),
        xp_reward=fight_xp(tier, threat),
    )

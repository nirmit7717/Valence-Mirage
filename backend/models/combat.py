"""Combat models — state, combatants, enemies, status effects, actions."""

from pydantic import BaseModel, Field
from enum import Enum


class CombatActionType(str, Enum):
    ATTACK = "attack"
    SPELL = "spell"
    DEFEND = "defend"
    SUPPORT = "support"
    FLEE = "flee"


class StatusEffectType(str, Enum):
    """Canonical status effect identifiers."""
    BLEED = "bleed"
    STUN = "stun"
    WEAKEN = "weaken"
    FOCUS = "focus"
    # Existing legacy effects kept for backward compat
    POISONED = "poisoned"
    BURNING = "burning"
    BLOCKING = "blocking"
    HEALING = "healing"
    DODGING = "dodging"
    HIDDEN = "hidden"


# How each effect behaves during tick
STATUS_EFFECT_RULES: dict[str, dict] = {
    # ── New tactical effects ──
    StatusEffectType.BLEED: {
        "dot": (2, 4),        # random damage range per tick
        "skip_turn": False,
        "damage_modifier": 1.0,  # multiplier on outgoing damage
        "roll_modifier": 0,      # flat bonus to d20
        "armor_modifier": 0,
        "max_duration": 3,
        "stacks": False,         # refresh duration instead of stacking
    },
    StatusEffectType.STUN: {
        "dot": (0, 0),
        "skip_turn": True,
        "damage_modifier": 1.0,
        "roll_modifier": 0,
        "armor_modifier": 0,
        "max_duration": 1,
        "stacks": False,
    },
    StatusEffectType.WEAKEN: {
        "dot": (0, 0),
        "skip_turn": False,
        "damage_modifier": 0.5,  # halve outgoing damage
        "roll_modifier": 0,
        "armor_modifier": 0,
        "max_duration": 2,
        "stacks": False,
    },
    StatusEffectType.FOCUS: {
        "dot": (0, 0),
        "skip_turn": False,
        "damage_modifier": 1.0,
        "roll_modifier": 5,      # +5 to next d20 roll
        "armor_modifier": 0,
        "max_duration": 1,
        "stacks": False,
    },
    # ── Legacy effects (kept for existing abilities) ──
    StatusEffectType.POISONED: {
        "dot": (1, 4),
        "skip_turn": False,
        "damage_modifier": 1.0,
        "roll_modifier": 0,
        "armor_modifier": 0,
        "max_duration": 5,
        "stacks": False,
    },
    StatusEffectType.BURNING: {
        "dot": (1, 3),
        "skip_turn": False,
        "damage_modifier": 1.0,
        "roll_modifier": 0,
        "armor_modifier": 0,
        "max_duration": 3,
        "stacks": False,
    },
    StatusEffectType.BLOCKING: {
        "dot": (0, 0),
        "skip_turn": False,
        "damage_modifier": 1.0,
        "roll_modifier": 0,
        "armor_modifier": 3,
        "max_duration": 1,
        "stacks": False,
    },
    StatusEffectType.HEALING: {
        "dot": (-6, -2),  # negative = heal
        "skip_turn": False,
        "damage_modifier": 1.0,
        "roll_modifier": 0,
        "armor_modifier": 0,
        "max_duration": 3,
        "stacks": False,
    },
    StatusEffectType.DODGING: {
        "dot": (0, 0),
        "skip_turn": False,
        "damage_modifier": 1.0,
        "roll_modifier": 0,
        "armor_modifier": 0,
        "dodge_chance": 0.5,  # 50% chance to avoid attack
        "max_duration": 1,
        "stacks": False,
    },
    StatusEffectType.HIDDEN: {
        "dot": (0, 0),
        "skip_turn": False,
        "damage_modifier": 1.0,
        "roll_modifier": 3,  # bonus from stealth
        "armor_modifier": 0,
        "max_duration": 2,
        "stacks": False,
    },
}


def get_effect_rule(name: str) -> dict:
    """Look up effect rule by name string. Returns default if unknown."""
    return STATUS_EFFECT_RULES.get(
        name.lower(),
        {"dot": (0, 0), "skip_turn": False, "damage_modifier": 1.0,
         "roll_modifier": 0, "armor_modifier": 0, "max_duration": 5, "stacks": False}
    )


class StatusEffect(BaseModel):
    name: str
    duration: int  # turns remaining
    stat_modifier: dict[str, int] = {}  # {"strength": -2}
    damage_per_turn: int = 0
    armor_modifier: int = 0
    dodge_chance: float = 0.0  # 0.0 to 1.0


class Combatant(BaseModel):
    name: str
    hp: int
    max_hp: int
    armor: int
    attack_bonus: float  # added to d20
    mana: int = 0
    max_mana: int = 0
    is_player: bool = False
    abilities: list[dict] = []  # ability dicts from character.py
    status_effects: list[StatusEffect] = []


class EnemyTemplate(BaseModel):
    name: str
    tier: int  # 1-5
    hp: int
    armor: int
    attack_bonus: float
    damage_dice: str  # "1d8+2"
    abilities: list[dict] = []
    loot_table: list[dict] = []  # {"name": "...", "chance": 0.5, "type": "weapon"}
    xp_reward: int = 0


class CombatAction(BaseModel):
    actor: str  # "player" or enemy name
    action_type: CombatActionType
    ability_name: str = ""
    damage_dice: str = ""
    mana_cost: int = 0
    status_effect: str | None = None
    status_duration: int = 0
    target: str = ""  # enemy name or "player"


class CombatLogEntry(BaseModel):
    turn: int
    actor: str
    action: str
    result: str  # "hit", "miss", "crit", "blocked", "heal", etc.
    damage: int = 0
    message: str = ""


class CombatState(BaseModel):
    combat_id: str = ""
    enemies: list[Combatant] = []
    player: Combatant | None = None
    turn_number: int = 0
    current_turn: str = "player"  # "player" or "enemy"
    status: str = "active"  # "active", "victory", "defeat", "fled"
    log: list[CombatLogEntry] = []
    contextual_moves: list[dict] = []  # LLM-generated situational moves

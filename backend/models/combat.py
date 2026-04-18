"""Combat models — state, combatants, enemies, status effects, actions."""

from pydantic import BaseModel, Field
from enum import Enum


class CombatActionType(str, Enum):
    ATTACK = "attack"
    SPELL = "spell"
    DEFEND = "defend"
    SUPPORT = "support"
    FLEE = "flee"


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

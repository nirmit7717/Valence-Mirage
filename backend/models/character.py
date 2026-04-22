"""Character class system — classes, stats, abilities, starting equipment."""

from enum import Enum
from pydantic import BaseModel, Field


class CharacterClass(str, Enum):
    WARRIOR = "warrior"
    ROGUE = "rogue"
    WIZARD = "wizard"
    CLERIC = "cleric"
    BARD = "bard"


class Ability(BaseModel):
    name: str
    description: str
    ability_type: str  # "attack", "spell", "defend", "support"
    damage_dice: str = ""  # e.g. "2d6+3", empty for non-damage
    mana_cost: int = 0
    status_effect: str | None = None  # "stunned", "burning", "blessed", etc.
    status_duration: int = 0  # turns


class StatusEffect(BaseModel):
    name: str
    duration: int  # turns remaining
    stat_modifier: dict = {}  # {"strength": -2, "dexterity": 1}
    damage_per_turn: int = 0
    description: str = ""


# ─── Class Definitions ───

CLASS_STATS = {
    CharacterClass.WARRIOR: {
        "strength": 14, "intelligence": 8, "dexterity": 10,
        "control": 12, "charisma": 8, "wisdom": 8,
        "hp_bonus": 15, "mana_bonus": 0,
    },
    CharacterClass.ROGUE: {
        "strength": 10, "intelligence": 10, "dexterity": 14,
        "control": 8, "charisma": 10, "wisdom": 8,
        "hp_bonus": 5, "mana_bonus": 5,
    },
    CharacterClass.WIZARD: {
        "strength": 6, "intelligence": 14, "dexterity": 8,
        "control": 12, "charisma": 8, "wisdom": 12,
        "hp_bonus": -5, "mana_bonus": 20,
    },
    CharacterClass.CLERIC: {
        "strength": 10, "intelligence": 10, "dexterity": 8,
        "control": 10, "charisma": 10, "wisdom": 12,
        "hp_bonus": 5, "mana_bonus": 10,
    },
    CharacterClass.BARD: {
        "strength": 8, "intelligence": 10, "dexterity": 10,
        "control": 8, "charisma": 14, "wisdom": 10,
        "hp_bonus": 0, "mana_bonus": 10,
    },
}

CLASS_ABILITIES = {
    CharacterClass.WARRIOR: [
        Ability(name="Power Strike", description="A devastating blow with extra force",
                ability_type="attack", damage_dice="2d8+3", mana_cost=0),
        Ability(name="Shield Block", description="Raise your shield to absorb damage",
                ability_type="defend", mana_cost=0, status_effect="blocking", status_duration=1),
        Ability(name="Battle Cry", description="Rally yourself, boosting strength",
                ability_type="support", mana_cost=5, status_effect="battle_cry", status_duration=3),
        Ability(name="Cleave", description="A wide sweeping attack",
                ability_type="attack", damage_dice="1d12+5", mana_cost=0),
    ],
    CharacterClass.ROGUE: [
        Ability(name="Backstab", description="Strike from the shadows for massive damage",
                ability_type="attack", damage_dice="3d6+5", mana_cost=15),
        Ability(name="Dodge", description="Evade the next incoming attack",
                ability_type="defend", mana_cost=0, status_effect="dodging", status_duration=1),
        Ability(name="Poison Blade", description="Coat your weapon with poison",
                ability_type="attack", damage_dice="1d6+2", mana_cost=5,
                status_effect="poisoned", status_duration=3),
        Ability(name="Shadow Step", description="Vanish and reposition",
                ability_type="support", mana_cost=10, status_effect="hidden", status_duration=2),
    ],
    CharacterClass.WIZARD: [
        Ability(name="Fireball", description="Hurl a ball of fire at the enemy",
                ability_type="spell", damage_dice="3d8+4", mana_cost=15),
        Ability(name="Ice Shield", description="Create a barrier of ice",
                ability_type="defend", mana_cost=10, status_effect="ice_shield", status_duration=2),
        Ability(name="Lightning Bolt", description="A bolt of crackling energy",
                ability_type="spell", damage_dice="2d10+3", mana_cost=12,
                status_effect="stunned", status_duration=1),
        Ability(name="Arcane Barrier", description="A shimmering protective ward",
                ability_type="support", mana_cost=8, status_effect="arcane_barrier", status_duration=3),
    ],
    CharacterClass.CLERIC: [
        Ability(name="Heal", description="Restore health with divine light",
                ability_type="support", mana_cost=10),
        Ability(name="Smite", description="Strike with holy energy",
                ability_type="attack", damage_dice="2d8+3", mana_cost=8),
        Ability(name="Bless", description="Boost all stats temporarily",
                ability_type="support", mana_cost=12, status_effect="blessed", status_duration=3),
        Ability(name="Holy Shield", description="A shield of divine protection",
                ability_type="defend", mana_cost=8, status_effect="holy_shield", status_duration=2),
    ],
    CharacterClass.BARD: [
        Ability(name="Inspire", description="A rousing song that boosts morale",
                ability_type="support", mana_cost=8, status_effect="inspired", status_duration=3),
        Ability(name="Mock", description="A cutting insult that weakens the enemy",
                ability_type="attack", damage_dice="1d6", mana_cost=5,
                status_effect="weakened", status_duration=2),
        Ability(name="Charm", description="Mesmerize the enemy into inaction",
                ability_type="spell", mana_cost=10, status_effect="charmed", status_duration=1),
        Ability(name="Dissonance", description="A painful burst of magical sound",
                ability_type="attack", damage_dice="2d8+2", mana_cost=12),
    ],
}

CLASS_STARTING_GEAR = {
    CharacterClass.WARRIOR: [
        {"name": "Iron Sword", "type": "weapon", "damage_bonus": 2},
        {"name": "Wooden Shield", "type": "armor", "armor_bonus": 2},
        {"name": "Health Potion", "type": "consumable", "effect": "heal_20"},
    ],
    CharacterClass.ROGUE: [
        {"name": "Twin Daggers", "type": "weapon", "damage_bonus": 1},
        {"name": "Leather Vest", "type": "armor", "armor_bonus": 1},
        {"name": "Smoke Bomb", "type": "consumable", "effect": "hidden_2"},
    ],
    CharacterClass.WIZARD: [
        {"name": "Oak Staff", "type": "weapon", "damage_bonus": 1},
        {"name": "Mage Robes", "type": "armor", "armor_bonus": 0},
        {"name": "Mana Crystal", "type": "consumable", "effect": "mana_20"},
    ],
    CharacterClass.CLERIC: [
        {"name": "War Hammer", "type": "weapon", "damage_bonus": 2},
        {"name": "Chain Mail", "type": "armor", "armor_bonus": 3},
        {"name": "Holy Water", "type": "consumable", "effect": "heal_15"},
    ],
    CharacterClass.BARD: [
        {"name": "Rapier", "type": "weapon", "damage_bonus": 1},
        {"name": "Traveler's Cloak", "type": "armor", "armor_bonus": 1},
        {"name": "Lute", "type": "weapon", "damage_bonus": 0},
    ],
}

CLASS_DESCRIPTIONS = {
    CharacterClass.WARRIOR: "A battle-hardened fighter. High strength and health, excels in direct combat.",
    CharacterClass.ROGUE: "A cunning shadow-dancer. High dexterity, relies on precision and stealth.",
    CharacterClass.WIZARD: "A master of the arcane arts. High intelligence, devastating spells but fragile.",
    CharacterClass.CLERIC: "A divine warrior-healer. Balanced stats with healing and holy power.",
    CharacterClass.BARD: "A charismatic performer. High charisma, uses wit and magic to influence.",
}

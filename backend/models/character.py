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
        Ability(name="Power Strike", description="A devastating blow — high damage, lower accuracy",
                ability_type="attack", damage_dice="2d8+3", mana_cost=0),
        Ability(name="Guard", description="Brace for impact, reducing incoming damage next turn",
                ability_type="defend", mana_cost=0, status_effect="blocking", status_duration=1),
        Ability(name="Cleave", description="A wide sweeping attack that causes bleeding",
                ability_type="attack", damage_dice="1d12+5", mana_cost=0,
                status_effect="bleed", status_duration=3),
        Ability(name="War Cry", description="A fearsome shout that weakens nearby enemies",
                ability_type="support", mana_cost=5, status_effect="weaken", status_duration=2),
    ],
    CharacterClass.ROGUE: [
        Ability(name="Backstab", description="Strike from the shadows for massive damage",
                ability_type="attack", damage_dice="3d6+5", mana_cost=15),
        Ability(name="Evade", description="Dodge the next incoming attack",
                ability_type="defend", mana_cost=0, status_effect="dodging", status_duration=1),
        Ability(name="Poison Blade", description="Coat weapon with poison, causing damage over time",
                ability_type="attack", damage_dice="1d6+2", mana_cost=5,
                status_effect="poisoned", status_duration=3),
        Ability(name="Shadow Step", description="Slip into the shadows to boost your next strike",
                ability_type="support", mana_cost=8, status_effect="focus", status_duration=1),
    ],
    CharacterClass.WIZARD: [
        Ability(name="Arcane Bolt", description="Hurl a bolt of pure arcane energy",
                ability_type="spell", damage_dice="2d10+4", mana_cost=12),
        Ability(name="Focus Mind", description="Channel inner power, boosting your next roll",
                ability_type="support", mana_cost=8, status_effect="focus", status_duration=1),
        Ability(name="Lightning Bolt", description="A bolt of crackling energy that stuns",
                ability_type="spell", damage_dice="2d8+3", mana_cost=15,
                status_effect="stun", status_duration=1),
        Ability(name="Arcane Shield", description="Conjure a barrier of pure magic",
                ability_type="defend", mana_cost=10, status_effect="blocking", status_duration=1),
    ],
    CharacterClass.CLERIC: [
        Ability(name="Heal", description="Restore health with divine light",
                ability_type="support", mana_cost=10),
        Ability(name="Smite", description="Strike with holy energy that weakens the enemy",
                ability_type="attack", damage_dice="2d8+3", mana_cost=8,
                status_effect="weaken", status_duration=2),
        Ability(name="Holy Shield", description="A shield of divine protection",
                ability_type="defend", mana_cost=8, status_effect="blocking", status_duration=2),
        Ability(name="Purify", description="Cleanse ailments and sharpen the mind",
                ability_type="support", mana_cost=6, status_effect="focus", status_duration=1),
    ],
    CharacterClass.BARD: [
        Ability(name="Mock", description="A cutting insult that weakens the enemy",
                ability_type="attack", damage_dice="1d6", mana_cost=5,
                status_effect="weaken", status_duration=2),
        Ability(name="Inspire", description="A rousing song that sharpens your focus",
                ability_type="support", mana_cost=8, status_effect="focus", status_duration=1),
        Ability(name="Dissonance", description="A painful burst of magical sound",
                ability_type="attack", damage_dice="2d8+2", mana_cost=12),
        Ability(name="Lullaby", description="A soothing melody that stuns the enemy",
                ability_type="support", mana_cost=10, status_effect="stun", status_duration=1),
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

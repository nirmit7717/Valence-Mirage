"""Enemy templates — 5 tiers × 3 types, deterministic loot tables."""

from models.combat import EnemyTemplate

# Tier 1: Easy (early encounters)
ENEMY_TEMPLATES = {
    # ─── Tier 1: Scavengers ───
    "goblin_scavenger": EnemyTemplate(
        name="Goblin Scavenger", tier=1, hp=15, armor=1, attack_bonus=1.0,
        damage_dice="1d6+1", xp_reward=20,
        loot_table=[
            {"name": "Rusty Dagger", "type": "weapon", "chance": 0.3, "damage_bonus": 1},
            {"name": "Small Health Potion", "type": "consumable", "chance": 0.4, "hp_restore": 15},
        ],
    ),
    "skeleton_soldier": EnemyTemplate(
        name="Skeleton Soldier", tier=1, hp=18, armor=2, attack_bonus=0.5,
        damage_dice="1d8", xp_reward=25,
        loot_table=[
            {"name": "Bone Fragment", "type": "misc", "chance": 0.5},
            {"name": "Worn Shield", "type": "armor", "chance": 0.2, "armor_bonus": 1},
        ],
    ),
    "giant_rat": EnemyTemplate(
        name="Giant Rat", tier=1, hp=10, armor=0, attack_bonus=2.0,
        damage_dice="1d4+2", xp_reward=15,
        loot_table=[
            {"name": "Rat Tail", "type": "misc", "chance": 0.6},
        ],
    ),

    # ─── Tier 2: Soldiers ───
    "bandit_thug": EnemyTemplate(
        name="Bandit Thug", tier=2, hp=25, armor=3, attack_bonus=2.0,
        damage_dice="1d8+2", xp_reward=40,
        loot_table=[
            {"name": "Stolen Gold", "type": "misc", "chance": 0.5},
            {"name": "Leather Armor", "type": "armor", "chance": 0.3, "armor_bonus": 2},
            {"name": "Health Potion", "type": "consumable", "chance": 0.3, "hp_restore": 25},
        ],
    ),
    "corrupted_wolf": EnemyTemplate(
        name="Corrupted Wolf", tier=2, hp=22, armor=1, attack_bonus=3.0,
        damage_dice="2d4+2", xp_reward=35,
        abilities=[{"name": "Savage Bite", "damage_dice": "2d6+3", "status_effect": "bleeding", "status_duration": 2}],
        loot_table=[
            {"name": "Wolf Pelt", "type": "misc", "chance": 0.6},
        ],
    ),
    "undead_archer": EnemyTemplate(
        name="Undead Archer", tier=2, hp=20, armor=2, attack_bonus=2.5,
        damage_dice="1d10+1", xp_reward=40,
        loot_table=[
            {"name": "Cracked Bow", "type": "weapon", "chance": 0.2, "damage_bonus": 1},
            {"name": "Arrow Bundle", "type": "misc", "chance": 0.4},
        ],
    ),

    # ─── Tier 3: Veterans ───
    "dark_knight": EnemyTemplate(
        name="Dark Knight", tier=3, hp=40, armor=5, attack_bonus=3.0,
        damage_dice="1d12+3", xp_reward=70,
        abilities=[
            {"name": "Shield Slam", "damage_dice": "1d8+2", "status_effect": "stunned", "status_duration": 1},
            {"name": "Dark Slash", "damage_dice": "2d8+4"},
        ],
        loot_table=[
            {"name": "Dark Steel Sword", "type": "weapon", "chance": 0.3, "damage_bonus": 3},
            {"name": "Knight's Shield", "type": "armor", "chance": 0.2, "armor_bonus": 3},
            {"name": "Greater Health Potion", "type": "consumable", "chance": 0.4, "hp_restore": 40},
        ],
    ),
    "shadow_mage": EnemyTemplate(
        name="Shadow Mage", tier=3, hp=28, armor=2, attack_bonus=4.0,
        damage_dice="2d8+3", xp_reward=75,
        abilities=[
            {"name": "Shadow Bolt", "damage_dice": "2d10+3"},
            {"name": "Curse", "status_effect": "weakened", "status_duration": 2, "stat_modifier": {"strength": -3}},
        ],
        loot_table=[
            {"name": "Shadow Essence", "type": "misc", "chance": 0.5},
            {"name": "Mana Crystal", "type": "consumable", "chance": 0.4, "mana_restore": 30},
        ],
    ),
    "crypt_horror": EnemyTemplate(
        name="Crypt Horror", tier=3, hp=45, armor=3, attack_bonus=2.5,
        damage_dice="2d6+4", xp_reward=65,
        abilities=[{"name": "Terrifying Howl", "status_effect": "frightened", "status_duration": 2, "stat_modifier": {"dexterity": -2}}],
        loot_table=[
            {"name": "Ancient Relic", "type": "misc", "chance": 0.4},
            {"name": "Enchanted Ring", "type": "armor", "chance": 0.2, "stat_bonus": {"charisma": 2}},
        ],
    ),

    # ─── Tier 4: Elites ───
    "dragon_whelp": EnemyTemplate(
        name="Dragon Whelp", tier=4, hp=55, armor=6, attack_bonus=4.0,
        damage_dice="2d10+5", xp_reward=120,
        abilities=[
            {"name": "Fire Breath", "damage_dice": "3d8+5", "status_effect": "burning", "status_duration": 2},
            {"name": "Tail Swipe", "damage_dice": "2d8+3", "status_effect": "stunned", "status_duration": 1},
        ],
        loot_table=[
            {"name": "Dragon Scale", "type": "armor", "chance": 0.4, "armor_bonus": 4},
            {"name": "Dragon Tooth", "type": "weapon", "chance": 0.3, "damage_bonus": 4},
            {"name": "Superior Health Potion", "type": "consumable", "chance": 0.5, "hp_restore": 60},
        ],
    ),
    "vampire_lord": EnemyTemplate(
        name="Vampire Lord", tier=4, hp=50, armor=4, attack_bonus=5.0,
        damage_dice="2d8+4", xp_reward=130,
        abilities=[
            {"name": "Life Drain", "damage_dice": "2d8+3", "heal_self": True},
            {"name": "Blood Frenzy", "status_effect": "blessed", "status_duration": 3, "stat_modifier": {"strength": 4}},
        ],
        loot_table=[
            {"name": "Vampire Cape", "type": "armor", "chance": 0.3, "armor_bonus": 3},
            {"name": "Blood Ruby", "type": "misc", "chance": 0.5},
        ],
    ),
    "demon_guardian": EnemyTemplate(
        name="Demon Guardian", tier=4, hp=60, armor=5, attack_bonus=4.5,
        damage_dice="2d10+4", xp_reward=125,
        abilities=[
            {"name": "Hellfire", "damage_dice": "3d8+6", "status_effect": "burning", "status_duration": 2},
            {"name": "Demonic Roar", "status_effect": "frightened", "status_duration": 2, "stat_modifier": {"strength": -2, "dexterity": -2}},
        ],
        loot_table=[
            {"name": "Demon Horn", "type": "weapon", "chance": 0.3, "damage_bonus": 5},
            {"name": "Infernal Plate", "type": "armor", "chance": 0.2, "armor_bonus": 5},
        ],
    ),

    # ─── Tier 5: Bosses ───
    "ancient_dragon": EnemyTemplate(
        name="Ancient Dragon", tier=5, hp=100, armor=8, attack_bonus=6.0,
        damage_dice="3d10+6", xp_reward=250,
        abilities=[
            {"name": "Inferno Breath", "damage_dice": "4d10+8", "status_effect": "burning", "status_duration": 3},
            {"name": "Crushing Bite", "damage_dice": "3d12+6"},
            {"name": "Wing Buffet", "damage_dice": "2d10+4", "status_effect": "stunned", "status_duration": 1},
            {"name": "Ancient Rage", "status_effect": "blessed", "status_duration": 3, "stat_modifier": {"strength": 6}},
        ],
        loot_table=[
            {"name": "Dragon Heart", "type": "misc", "chance": 0.8},
            {"name": "Legendary Blade", "type": "weapon", "chance": 0.5, "damage_bonus": 7},
            {"name": "Dragon Scale Armor", "type": "armor", "chance": 0.4, "armor_bonus": 6},
        ],
    ),
    "lich_king": EnemyTemplate(
        name="Lich King", tier=5, hp=80, armor=5, attack_bonus=7.0,
        damage_dice="3d8+5", xp_reward=250,
        abilities=[
            {"name": "Death Ray", "damage_dice": "4d10+6"},
            {"name": "Soul Drain", "damage_dice": "3d8+4", "heal_self": True},
            {"name": "Necrotic Plague", "status_effect": "poisoned", "status_duration": 3, "stat_modifier": {"strength": -4}},
            {"name": "Raise Dead", "heal_self": True},  # heals on successful use
        ],
        loot_table=[
            {"name": "Lich's Phylactery", "type": "misc", "chance": 0.7},
            {"name": "Staff of Souls", "type": "weapon", "chance": 0.4, "damage_bonus": 6},
            {"name": "Crown of the Dead", "type": "armor", "chance": 0.3, "stat_bonus": {"intelligence": 4, "wisdom": 4}},
        ],
    ),
    "demon_lord": EnemyTemplate(
        name="Demon Lord", tier=5, hp=90, armor=7, attack_bonus=6.5,
        damage_dice="3d10+7", xp_reward=250,
        abilities=[
            {"name": "Apocalypse Strike", "damage_dice": "4d12+8"},
            {"name": "Hellstorm", "damage_dice": "3d10+5", "status_effect": "burning", "status_duration": 2},
            {"name": "Corrupting Presence", "status_effect": "weakened", "status_duration": 3, "stat_modifier": {"strength": -3, "intelligence": -3}},
        ],
        loot_table=[
            {"name": "Demon Lord's Horn", "type": "weapon", "chance": 0.5, "damage_bonus": 8},
            {"name": "Abyssal Armor", "type": "armor", "chance": 0.4, "armor_bonus": 7},
            {"name": "Elixir of Power", "type": "consumable", "chance": 0.6, "stat_bonus": {"strength": 3}},
        ],
    ),
}

# Quick lookup by tier
ENEMIES_BY_TIER: dict[int, list[str]] = {i: [] for i in range(1, 6)}
for key, tmpl in ENEMY_TEMPLATES.items():
    ENEMIES_BY_TIER[tmpl.tier].append(key)


def get_random_enemy(tier: int, rng=None) -> EnemyTemplate:
    """Pick a random enemy template for a given tier."""
    import random
    keys = ENEMIES_BY_TIER.get(tier, [])
    if not keys:
        keys = ENEMIES_BY_TIER[1]
    key = rng.choice(keys) if rng else random.choice(keys)
    return ENEMY_TEMPLATES[key]


def roll_loot(enemy: EnemyTemplate, rng=None) -> list[dict]:
    """Roll deterministic loot from an enemy's loot table."""
    import random
    r = rng or random
    items = []
    for entry in enemy.loot_table:
        if r.random() < entry.get("chance", 0.5):
            items.append(entry)
    return items


def roll_damage(dice_str: str, rng=None) -> int:
    """Parse dice notation (e.g. '2d8+3') and roll."""
    import random
    r = rng or random
    if not dice_str:
        return 0
    import re
    match = re.match(r"(\d+)d(\d+)([+-]\d+)?", dice_str)
    if not match:
        return 0
    count = int(match.group(1))
    sides = int(match.group(2))
    modifier = int(match.group(3) or 0)
    return sum(r.randint(1, sides) for _ in range(count)) + modifier

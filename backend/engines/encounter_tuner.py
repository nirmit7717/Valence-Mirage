"""Encounter Tuner — adjust combat encounter frequency and difficulty from player profile."""

import random
import logging
from typing import Optional

from models.profile import PlayerProfile

logger = logging.getLogger(__name__)

# Base encounter parameters
BASE_COMBAT_TENSION_THRESHOLD = 6     # Turns of tension before forced combat
BASE_ENEMY_TIER_BONUS = 0             # Added to enemy tier rolls
BASE_LOOT_QUALITY = 0.5               # 0.0-1.0 quality multiplier


def get_encounter_params(profile: Optional[PlayerProfile]) -> dict:
    """Derive encounter parameters from player profile.

    Returns dict with:
        tension_threshold: How many tension points before forced combat
        enemy_tier_bonus: Bonus to enemy difficulty tier
        loot_quality: Quality of loot drops (0.0-1.0)
        min_combat_beats: Minimum combat beats in campaign
        max_combat_beats: Maximum combat beats in campaign
    """
    if profile is None:
        return {
            "tension_threshold": BASE_COMBAT_TENSION_THRESHOLD,
            "enemy_tier_bonus": BASE_ENEMY_TIER_BONUS,
            "loot_quality": BASE_LOOT_QUALITY,
            "min_combat_beats": 2,
            "max_combat_beats": 6,
        }

    combat_aff = profile.combat_affinity
    risk = profile.risk_tolerance

    # Higher combat affinity → more frequent combat (lower threshold)
    tension_threshold = max(3, min(10, BASE_COMBAT_TENSION_THRESHOLD - int(combat_aff * 3)))

    # Higher risk tolerance → harder enemies, better loot
    enemy_tier_bonus = max(0, min(2, int(risk * 2)))
    loot_quality = max(0.3, min(1.0, 0.5 + risk * 0.3))

    # Combat beat range based on affinity
    min_beats = max(1, int(2 + combat_aff * 2))
    max_beats = max(min_beats + 1, int(6 + combat_aff * 3))

    params = {
        "tension_threshold": tension_threshold,
        "enemy_tier_bonus": enemy_tier_bonus,
        "loot_quality": loot_quality,
        "min_combat_beats": min_beats,
        "max_combat_beats": max_beats,
    }

    logger.debug(f"Encounter params from profile: {params}")
    return params


def adjust_enemy_stats(enemy: dict, profile: Optional[PlayerProfile]) -> dict:
    """Adjust a generated enemy's stats based on player profile.

    Modifies HP, armor, and attack_bonus in-place and returns the enemy dict.
    """
    if profile is None:
        return enemy

    params = get_encounter_params(profile)

    # Scale HP by tier bonus (±15% per bonus level)
    tier_bonus = params["enemy_tier_bonus"]
    hp_scale = 1.0 + tier_bonus * 0.15
    enemy["hp"] = int(enemy.get("hp", 30) * hp_scale)
    enemy["max_hp"] = enemy["hp"]

    # Scale armor slightly
    if tier_bonus > 0:
        enemy["armor"] = enemy.get("armor", 0) + tier_bonus

    return enemy

"""Normalize item definitions (class gear, loot tables) into the Item model.

Gear and loot definitions use flat keys such as ``armor_bonus``,
``damage_bonus`` and ``effect: "heal_20"``. Combat and inventory code read
``Item.stat_bonus``, ``hp_restore`` and ``mana_restore``, so every item must be
built through ``item_from_definition`` to keep those values.
"""

import re

from models.game_state import Item

# Flat bonus keys that belong in Item.stat_bonus.
_BONUS_KEYS = ("armor_bonus", "damage_bonus")

# Effect strings like "heal_20" / "mana_15" map to restore fields.
_EFFECT_PATTERN = re.compile(r"^(heal|mana)_(\d+)$")


def item_from_definition(entry: dict, description: str = "") -> Item:
    """Build an Item from a gear/loot dict, preserving bonuses and consumable effects."""
    item_type = entry.get("type") or entry.get("item_type") or "misc"

    stat_bonus = {key: int(value) for key, value in (entry.get("stat_bonus") or {}).items()}
    for key in _BONUS_KEYS:
        value = int(entry.get(key) or 0)
        if value:
            stat_bonus[key] = stat_bonus.get(key, 0) + value

    hp_restore = int(entry.get("hp_restore") or 0)
    mana_restore = int(entry.get("mana_restore") or 0)
    match = _EFFECT_PATTERN.match(str(entry.get("effect") or ""))
    if match:
        kind, amount = match.group(1), int(match.group(2))
        if kind == "heal":
            hp_restore = max(hp_restore, amount)
        else:
            mana_restore = max(mana_restore, amount)

    return Item(
        name=entry["name"],
        description=entry.get("description") or description,
        item_type=item_type,
        stat_bonus=stat_bonus,
        hp_restore=hp_restore,
        mana_restore=mana_restore,
        consumes_on_use=item_type == "consumable",
    )

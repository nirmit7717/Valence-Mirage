"""Milestone leveling and story-scaled enemies.

XP comes from playing the story, not from dice luck:

- every counted story turn: ``ACTION_XP``
- every finished beat: ``beat_xp(act_number)`` (later acts are worth more)
- every won fight: ``fight_xp(tier, threat)``

Enemy tier follows story progress (``story_tier``) and threat follows the
outline (``fight_threat``), so a campaign size always ends around the same
level: Short ~3, Standard ~4, Grand Saga ~6.

``PlayerState.xp`` is progress inside the current level and ``xp_to_next`` is
what the current level needs (so the HUD bar is ``xp / xp_to_next``).

Pure functions only — no app state, no I/O.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from engines import pacing

# Total XP needed to reach each level.
LEVEL_THRESHOLDS = {1: 0, 2: 100, 3: 230, 4: 400, 5: 600, 6: 800, 7: 1050, 8: 1350}
_MAX_TABLE_LEVEL = max(LEVEL_THRESHOLDS)
_PAST_TABLE_GROWTH = 50  # each level past the table needs this much more than the one before

ACTION_XP = 5
BEAT_XP = 20
BEAT_XP_PER_ACT = 5

FIGHT_TIER_XP = {1: 25, 2: 35, 3: 45, 4: 60, 5: 80}
THREAT_XP = {"minion": 0.5, "standard": 1.0, "elite": 1.5, "boss": 2.5}

# Level-up growth per class: +1 primary stat every level, +1 secondary on even levels.
CLASS_GROWTH = {
    "warrior": {"primary": "strength", "secondary": "control", "hp": 8, "mana": 3},
    "cleric": {"primary": "wisdom", "secondary": "charisma", "hp": 7, "mana": 7},
    "rogue": {"primary": "dexterity", "secondary": "charisma", "hp": 6, "mana": 5},
    "bard": {"primary": "charisma", "secondary": "dexterity", "hp": 6, "mana": 7},
    "wizard": {"primary": "intelligence", "secondary": "control", "hp": 5, "mana": 8},
}
LEVEL_UP_HEAL = 0.3  # share of max HP and mana restored on level-up

# Enemy tier at the start and end of each campaign size.
SIZE_TIER_RANGE = {"small": (1, 2), "medium": (1, 3), "large": (1, 4)}


def _half_up(value: float) -> int:
    return int(value + 0.5)


def _clamp_tier(tier: int) -> int:
    return max(1, min(5, int(tier)))


# ─── XP tables ───


def xp_for_next_level(level: int) -> int:
    """XP needed to go from ``level`` to ``level + 1``."""
    level = max(1, int(level))
    if level + 1 in LEVEL_THRESHOLDS:
        return LEVEL_THRESHOLDS[level + 1] - LEVEL_THRESHOLDS[level]
    last_step = LEVEL_THRESHOLDS[_MAX_TABLE_LEVEL] - LEVEL_THRESHOLDS[_MAX_TABLE_LEVEL - 1]
    return last_step + _PAST_TABLE_GROWTH * (level - _MAX_TABLE_LEVEL + 1)


def level_threshold(level: int) -> int:
    """Total XP at which ``level`` is reached."""
    if level in LEVEL_THRESHOLDS:
        return LEVEL_THRESHOLDS[level]
    return sum(xp_for_next_level(lv) for lv in range(1, max(1, level)))


def total_xp(player) -> int:
    return level_threshold(player.level) + player.xp


def beat_xp(act_number: int) -> int:
    """XP for finishing a beat in the ``act_number``-th act (1-based)."""
    return BEAT_XP + BEAT_XP_PER_ACT * max(0, int(act_number) - 1)


def fight_xp(tier: int, threat: str = "standard") -> int:
    return _half_up(FIGHT_TIER_XP[_clamp_tier(tier)] * THREAT_XP.get(threat, 1.0))


# ─── Awarding XP ───


def normalize(player) -> None:
    """Bring a player saved under an older XP curve onto this one."""
    player.xp_to_next = xp_for_next_level(player.level)


def _level_up(player, reason: str) -> dict:
    growth = CLASS_GROWTH.get((player.character_class or "").lower(), CLASS_GROWTH["warrior"])
    player.level += 1
    stats = {growth["primary"]: 1}
    if player.level % 2 == 0:
        stats[growth["secondary"]] = 1
    for stat, delta in stats.items():
        setattr(player.stats, stat, getattr(player.stats, stat) + delta)
    player.max_hp += growth["hp"]
    player.max_mana += growth["mana"]
    player.hp = min(player.max_hp, player.hp + round(player.max_hp * LEVEL_UP_HEAL))
    player.mana = min(player.max_mana, player.mana + round(player.max_mana * LEVEL_UP_HEAL))
    return {
        "level": player.level,
        "reason": reason,
        "hp_gain": growth["hp"],
        "mana_gain": growth["mana"],
        "stats": stats,
        "max_hp": player.max_hp,
        "max_mana": player.max_mana,
    }


def award(player, amount: int, reason: str = "") -> list[dict]:
    """Add XP and apply every level-up it earns. Returns the level-ups, oldest first."""
    normalize(player)
    if amount <= 0:
        return []
    player.xp += int(amount)
    level_ups = []
    while player.xp >= player.xp_to_next:
        player.xp -= player.xp_to_next
        level_ups.append(_level_up(player, reason))
        player.xp_to_next = xp_for_next_level(player.level)
    return level_ups


@dataclass
class XpLedger:
    """Everything one request awarded, for the response."""

    gained: int = 0
    level_ups: list[dict] = field(default_factory=list)

    def award(self, player, amount: int, reason: str) -> list[dict]:
        level_ups = award(player, amount, reason)
        self.gained += max(0, int(amount))
        self.level_ups.extend(level_ups)
        return level_ups


# ─── Story-scaled enemies ───


def act_number(campaign) -> int:
    """1-based position of the current beat's act."""
    acts = sorted({act.get("act_id", 0) for act, _ in pacing.ordered_beats(campaign)})
    if not acts:
        return 1
    current_act, _ = pacing.ordered_beats(campaign)[pacing.current_index(campaign)]
    return acts.index(current_act.get("act_id", 0)) + 1


def story_tier(campaign, size: str | None) -> int:
    """Enemy tier for the current beat: rises from the size's first tier to its last."""
    start, end = SIZE_TIER_RANGE.get(size or "", SIZE_TIER_RANGE["medium"])
    beats = pacing.ordered_beats(campaign)
    if len(beats) <= 1:
        return end
    # Half-up rounding of index * (end - start) / (beats - 1), in integers.
    steps, span = pacing.current_index(campaign) * (end - start), len(beats) - 1
    return _clamp_tier(start + (2 * steps + span) // (2 * span))


def fight_threat(campaign, surprise: bool = False) -> str:
    """The story decides how dangerous a fight is: the final beat is the boss,
    hinted beats are elite, everything else (and every surprise fight) is standard."""
    if surprise:
        return "standard"
    beat = pacing.current_beat(campaign) or {}
    hint = beat.get("threat_hint")
    if hint in ("elite", "boss"):
        return hint
    if pacing.is_final_beat(campaign):
        return "boss"
    return "standard"

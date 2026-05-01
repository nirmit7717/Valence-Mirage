"""Deviation Evaluator — Checks if player actions align with the campaign narrative.

Lightweight keyword/context matching. No LLM calls.
Returns a deviation classification and alignment score.
"""

import logging
import re

logger = logging.getLogger(__name__)

# Categories of relevance
RELEVANT = "relevant"              # Directly tied to current beat/objective
CREATIVE_VALID = "creative_valid"  # Not obvious but logically connected
SLIGHT_DEVIATION = "slight"        # Tangential but not disruptive
MAJOR_DEVIATION = "major"          # Clearly off-track

# Thresholds
SLIGHT_THRESHOLD = 0.15   # alignment below this → slight deviation
MAJOR_THRESHOLD = -0.1    # alignment below this → major deviation


def evaluate_alignment(
    action: str,
    current_beat: str | None,
    recent_narration: str,
    campaign_objective: str,
    location: str,
    npc_names: list[str] | None = None,
) -> tuple[str, float]:
    """Evaluate how well a player action aligns with the campaign.

    Returns:
        (classification: str, alignment_score: float)
        alignment_score ranges from -1.0 (completely off-track) to +1.0 (perfectly aligned)
    """
    action_lower = action.lower().strip()
    tokens = set(re.findall(r'\b\w{3,}\b', action_lower))

    if not tokens:
        return RELEVANT, 0.0  # Empty/short actions get benefit of doubt

    score = 0.0
    connection_found = False

    # Common stop words to filter from context matching
    common = {'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'her',
              'was', 'one', 'our', 'out', 'had', 'has', 'his', 'how', 'its', 'may',
              'new', 'now', 'old', 'see', 'way', 'who', 'did', 'get', 'let', 'say',
              'she', 'too', 'use', 'from', 'with', 'this', 'that', 'into', 'over'}

    # 1. Check against current beat title/description
    if current_beat:
        beat_tokens = set(re.findall(r'\b\w{3,}\b', current_beat.lower())) - common
        overlap = tokens & beat_tokens
        if overlap:
            score += min(0.4, len(overlap) * 0.1)
            connection_found = True

    # 2. Check against recent narration (last ~300 chars)
    if recent_narration:
        narr_tokens = set(re.findall(r'\b\w{3,}\b', recent_narration[-300:].lower())) - common
        overlap = tokens & narr_tokens
        if overlap:
            if len(overlap) >= 2:
                score += min(0.3, len(overlap) * 0.05)
                connection_found = True
            elif all(len(w) >= 5 for w in overlap):
                score += 0.1
                connection_found = True

    # 3. Check against campaign objective
    if campaign_objective:
        obj_tokens = set(re.findall(r'\b\w{3,}\b', campaign_objective.lower()))
        overlap = tokens & obj_tokens
        if overlap:
            score += min(0.3, len(overlap) * 0.1)
            connection_found = True

    # 4. Check against current location
    if location:
        loc_tokens = set(re.findall(r'\b\w{3,}\b', location.lower()))
        overlap = tokens & loc_tokens
        if overlap:
            score += min(0.2, len(overlap) * 0.1)
            connection_found = True

    # 5. Check against NPC names
    if npc_names:
        for name in npc_names:
            if name.lower() in action_lower:
                score += 0.3
                connection_found = True
                break

    # 6. Action type keywords that are always valid (only basic exploration/interaction)
    always_valid = {
        "look", "search", "examine", "inspect", "investigate",
        "listen", "watch", "observe", "explore",
        "talk", "speak", "ask", "tell",
        "rest", "wait", "hide", "sneak",
        "attack", "fight", "defend", "block", "dodge", "cast", "heal",
        "use", "drink", "eat", "equip",
        "help", "save", "protect", "find", "seek",
    }
    if tokens & always_valid:
        score += 0.15
        connection_found = True

    # 7. Penalty for completely disconnected actions
    if not connection_found and score <= 0:
        score -= 0.35  # Stronger penalty for truly disconnected actions
    elif not connection_found:
        score -= 0.2  # Even with a small positive score, lack of connection is penalized

    # Clamp
    score = max(-1.0, min(1.0, score))

    # Classify
    if score >= SLIGHT_THRESHOLD:
        classification = RELEVANT
    elif score >= 0.0:
        classification = CREATIVE_VALID  # Positive but below threshold = creative
    elif score >= MAJOR_THRESHOLD:
        classification = SLIGHT_DEVIATION
    else:
        classification = MAJOR_DEVIATION

    # False positive check: if STRONG connection exists, never classify as major
    # A single weak overlap shouldn't prevent major classification for truly off-track actions
    if classification == MAJOR_DEVIATION and score >= -0.1:
        classification = SLIGHT_DEVIATION

    # Common verbs alone don't prevent major classification
    # Only prevent if the action has SPECIFIC game verbs (attack, cast, etc.)
    game_verbs = {"attack", "fight", "defend", "cast", "heal", "use", "equip", "drink", "think", "try", "wait"}
    if classification == MAJOR_DEVIATION and (tokens & game_verbs):
        classification = SLIGHT_DEVIATION

    return classification, score


# Immersive warning messages for deviations
WARNING_MESSAGES = {
    1: [
        "A strange unease settles over you — this path feels disconnected from your purpose.",
        "You pause, sensing that your current direction may not serve your quest.",
        "Something tugs at the edge of your awareness, as if reminding you of your true goal.",
    ],
    2: [
        "The world around you seems to dim, as if rejecting your wandering attention.",
        "A cold wind carries a whisper — your focus is slipping.",
        "The narrative threads around you grow thin. You feel the story straining to hold.",
    ],
    3: [
        "The threads of fate snap. Your journey collapses into formless void.",
        "You have strayed too far from your path. The world forgets you.",
        "The story can no longer sustain your wandering. Darkness claims the narrative.",
    ],
}

import random

def get_warning_message(warning_count: int) -> str | None:
    """Get an immersive warning message for the given warning level."""
    if warning_count <= 0:
        return None
    level = min(warning_count, 3)
    return random.choice(WARNING_MESSAGES[level])
